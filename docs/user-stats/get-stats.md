# User Stats Query Design

## API

### 1. 스텟 종합 조회

### 보여주는 정보
- 특정 기간의 일별 상태 (실패 / 힌트O 성공 / 힌트X 성공 / 미시도 / 서버 장애)
- 현재 연속 정답 일수, 최고 연속 정답 일수
- 전체 정답 일수(총 몇번 정답 맞췄는지), 정답을 맞췄을 때 평균 시도 횟수/평균 힌트 수

```
GET /v2/stats?start_date=2025-03-12&end_date=2026-03-12
```

- Auth: `get_required_user`
- calendar(`start_date ~ end_date`) + summary(전체 기록 기반)를 함께 반환

```json
{
  "calendar": [
    { "date": "2026-03-10", "status": "SUCCESS_WITHOUT_HINT" },
    { "date": "2026-03-09", "status": "SUCCESS_WITH_HINT" },
    { "date": "2026-03-08", "status": "FAIL" },
    { "date": "2026-01-15", "status": "OUTAGE" }
  ],
  "summary": {
    "total_success_days": 45,
    "current_streak": 3,
    "max_streak": 12,
    "avg_guess_when_correct": 15.2,
    "avg_hints_when_correct": 1.3
  }
}
```

### 2. 특정 날짜 상세 조회

```
GET /v2/stats/{user_id}/{date}
```

- Auth 불필요 — `user_id`를 path parameter로 직접 받음
- Redis only — 데이터 없으면 404 (TTL 48시간, 오늘/어제만 조회 가능)

```json
{
  "date": "2026-03-12",
  "status": "FAIL",
  "guess_count": 15,
  "hint_count": 2
}
```


## 상태 매핑

DB에는 `SUCCESS` / `FAIL` / `GIVEUP` + `hint_count` 저장. 서버에서 5종 상태로 변환:

| 응답 상태 | 변환 조건 |
|---|---|
| `SUCCESS_WITHOUT_HINT` | `status=SUCCESS && hint_count==0` |
| `SUCCESS_WITH_HINT` | `status=SUCCESS && hint_count>0` |
| `FAIL` | `status=FAIL` 또는 `status=GIVEUP` |
| `OUTAGE` | `outage_dates`에 해당 날짜 존재 **(최우선 판정)** |
| (미시도) | calendar에 해당 날짜 없음 (프론트 판단) |

> OUTAGE 판정이 최우선: 장애가 도중에 발생할 수 있어 FAIL/SUCCESS와 공존 가능. `outage_dates`에 있으면 무조건 `OUTAGE`로 반환.


## 데이터 조회 흐름

게임 중 stat은 Redis에만 기록되고, daily batch로 DB에 flush되는 구조.

### 종합 조회 처리 순서
1. **DB 1회 full scan**: 해당 유저의 전체 기록 조회 (`ORDER BY quiz_date`)
2. **Redis 머지**: 오늘 데이터가 Redis에 있으면 DB 결과에 머지 (같은 `(user_id, quiz_date)` → Redis 우선)
3. **outage_dates 조회**: DB 직접 조회 (캐싱 없음, 10건 미만이라 불필요)
4. **Python 1회 순회**로 모든 집계 처리:
   - calendar 필터링 (`start_date ~ end_date` 범위 + outage 상태 매핑)
   - current_streak (역순 탐색, OUTAGE skip)
   - max_streak (전체 순회, OUTAGE skip)
   - total_success_days, avg_guess_when_correct, avg_hints_when_correct

### 캐싱
- 본인 데이터만 조회하므로 `Cache-Control: private`으로 충분
- SUCCESS/GIVEUP 시 프론트에서 캐시 무효화


## outage_dates 테이블 (Supabase)

| 컬럼 | 타입 |
|---|---|
| `date` | date, PK |
| `created_at` | timestamp, default now() |

- admin API로 등록/삭제
- 캐싱 없이 DB 직접 조회 (10건 미만)
