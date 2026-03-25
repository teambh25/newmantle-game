# Daily Batch API Design: Redis → DB Flush

## 개요

게임 중 Redis에만 기록된 stat 데이터를 외부 스케줄러(Airflow)의 API 호출로 DB에 flush하는 배치 엔드포인트.

- **패턴**: Write-Behind — 게임 중 DB write 없이, 배치에서 일괄 처리
- **멱등성**: `INSERT ... ON CONFLICT DO UPDATE`로 동일 배치 재실행해도 안전
- **인증**: Admin Basic Auth (기존 admin 엔드포인트와 동일 패턴)

---

## 결정 사항

| 항목 | 결정 | 비고 |
|------|------|------|
| flush 범위 | **날짜 지정 flush** | Airflow에서 대상 날짜를 전달. 멱등성으로 재실행 안전 |
| flush 후 Redis 키 | **TTL 만료까지 유지** (삭제 안 함) | 현재 유저 규모가 적어 메모리 이슈 없음 |
| 청크 사이즈 | **상수 1000** | service 내 `CHUNK_SIZE = 1000` |
| 배치 타이밍 | **데이터 확인 후 결정** | 가장 한적한 시간에 실행 예정 |
| 부분 실패 시 응답 | **500 반환 후 재실행** | 멱등성 보장으로 재실행해도 안전 |
| 키 탐색 방식 | **SCAN** (별도 index Set 없음) | 1만 개 미만 keyspace에서 SCAN은 수 ms. Set index는 쓰기 복잡도만 증가 |

---

## API 명세

### `POST /admin/stats/flush`

특정 날짜의 Redis stat 데이터를 DB로 flush한다.

#### Request

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `date` | `string (YYYY-MM-DD)` | Yes | flush 대상 날짜 |

```json
{
  "date": "2026-03-15"
}
```

#### Response

**200 OK** — flush 성공

```json
{
  "date": "2026-03-15",
  "flushed_count": 142,
  "skipped_count": 3
}
```

| 필드 | 설명 |
|------|------|
| `date` | flush 대상 날짜 |
| `flushed_count` | DB에 upsert된 레코드 수 |
| `skipped_count` | 유효하지 않은 데이터로 skip된 수 (status 필드 누락 등) |

#### Authentication

```
Authorization: Basic base64(username:password)
```

기존 `authenticate_admin` dependency 사용.

---

## 배치 처리 흐름

```
Airflow (trigger)
  │
  ▼
POST /admin/stats/flush  { date: "2026-03-15" }
  │
  ▼
┌─────────────────────────────────────────┐
│ 1. SCAN Redis: user:*:quiz:{date}:stat │
│ 2. HGETALL per key → parse             │
│ 3. Batch UPSERT to DB                  │
│ 4. Return summary                      │
└─────────────────────────────────────────┘
```

### Step 1: Redis SCAN

- 패턴: `user:*:quiz:{date}:stat` (지정 날짜만)
- `SCAN` cursor-based iteration 사용 (KEYS 명령 사용 금지 — blocking 위험)
- `count` 힌트: 100 (Redis 내부 최적화용, 정확한 반환 수가 아님)
- 별도 index Set 불필요 — 1만 개 미만 keyspace에서 SCAN은 수 ms로 완료

```python
pattern = f"user:*:quiz:{date}:stat"
keys = []
async for key in redis.scan_iter(match=pattern, count=100):
    keys.append(key)
```

### Step 2: Hash 데이터 읽기 + 파싱

Pipeline으로 HGETALL 일괄 호출하여 네트워크 라운드트립 최소화.

```python
async with redis.pipeline(transaction=False) as pipe:
    for key in keys:
        pipe.hgetall(key)
    responses = await pipe.execute()
```

키에서 `user_id` 추출 (`date`는 request에서 이미 알고 있음):

```
user:{user_id}:quiz:{date}:stat
      split(":")[1]
```

Hash fields → `QuizResultEntry` DTO 매핑:

| Redis Hash field | `QuizResultEntry` field | 변환 |
|------------------|------------------------|------|
| `status` | `status` | `UserQuizStatus` enum (`SUCCESS` / `FAIL` / `GIVEUP`) |
| `guesses` | `guess_count` | `int()`, 누락 시 0 |
| `hints` | `hint_count` | `int()`, 누락 시 0 |

**유효성 검사**:
- `status` 필드가 없거나 유효하지 않은 경우 → skip + 로깅 (skipped_count 증가)
- `guesses`/`hints` 필드 누락 시 → 0으로 기본값 처리

### Step 3: DB Batch UPSERT

기존 `StatRepository.upsert_results()` 메서드 활용.

```sql
INSERT INTO user_quiz_results (user_id, quiz_date, status, guess_count, hint_count)
VALUES (...)
ON CONFLICT (user_id, quiz_date) DO UPDATE SET
  status = EXCLUDED.status,
  guess_count = EXCLUDED.guess_count,
  hint_count = EXCLUDED.hint_count
```

- **청크 분할**: 1000건 단위 (상수 `CHUNK_SIZE`)
- **트랜잭션**: 청크 단위 커밋 — 중간 실패 시 이미 커밋된 청크는 유지, 멱등성에 의해 재실행 시 복구

---

## 스키마

```python
# schemas/stats.py에 추가

class FlushRequest(BaseModel):
    date: datetime.date

class FlushResponse(BaseModel):
    date: datetime.date
    flushed_count: int
    skipped_count: int
```

---

## 에러 처리

| 상황 | 대응 |
|------|------|
| Redis 연결 실패 | 500 에러 반환. Airflow에서 재시도 |
| Redis SCAN 중 부분 실패 | scan_iter가 cursor 기반이므로 연결 끊기면 전체 실패 → 재시도 |
| DB 연결 실패 | 500 에러 반환. Airflow에서 재시도 |
| 청크 upsert 중 부분 실패 | 실패 시 500 반환. 재실행 시 멱등성으로 안전 복구 |
| 개별 키 파싱 실패 | skip + warn 로깅. 나머지 정상 처리 계속 |

---

## Airflow 연동

### DAG 설정

| 항목 | 값 |
|------|-----|
| schedule | 데이터 확인 후 결정 (가장 한적한 시간대) |
| retry | 3회, 간격 5분 |
| timeout | 5분 |

### 호출 예시

```bash
curl -X POST https://api.newmantle.com/admin/stats/flush \
  -H "Authorization: Basic $(echo -n 'admin:password' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-03-15"}'
```

### 실패 시 수동 재실행

동일 날짜로 재호출. 멱등성으로 안전. 여러 날짜는 반복 호출:

```bash
for date in 2026-03-13 2026-03-14 2026-03-15; do
  curl -X POST https://api.newmantle.com/admin/stats/flush \
    -H "Authorization: Basic $AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"date\": \"$date\"}"
done
```

> Redis TTL(7일) 이내의 날짜만 데이터가 존재. TTL 초과 날짜는 flushed_count=0으로 정상 반환.

---

## 데이터 유실 리스크

| 리스크 | 확률 | 대응 |
|--------|------|------|
| 배치 전 Redis 장애로 데이터 유실 | 낮음 | Redis AOF 활성화. Redis 장애 시 게임 자체 불가하므로 stat만의 문제 아님 |
| 배치 실행 누락 (Airflow 장애) | 낮음 | Redis TTL 7일 → 7일 이내 수동 재실행 가능. Airflow 알림 설정 |
| TTL 만료 후 미flush 데이터 존재 | 극히 낮음 | 해당 stat 영구 누락. 모니터링으로 사전 감지 |

---

## 파일 변경 요약

| 구분 | 파일 | 변경 내용 |
|------|------|-----------|
| ~~수정~~ | ~~`cores/config.py`~~ | ~~불필요 — 청크 사이즈는 service 상수~~ |
| 수정 | `features/stats/repository.py` | `scan_redis_stats(date)` 메서드 추가. `QuizResultEntry` DTO 활용 |
| 수정 | `features/stats/service.py` | `flush_to_db(date)` 메서드 추가 |
| 수정 | `features/admin/routers.py` | `POST /admin/stats/flush` 엔드포인트 추가 |
| 수정 | `schemas/admin.py` | `FlushRequest`, `FlushResponse` 스키마 추가 |
