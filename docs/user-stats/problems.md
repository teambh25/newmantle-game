#  user stats problem : 유저 스탯 집계 로직에서 발생한 문제들

## 문제 상황

### Dual Write Problem (Redis ↔ DB 불일치)
- Redis와 DB에 데이터를 모두 쓰다보면 Dual Write Problem이 발생할 수 있음
  (Redis와 DB쓰기가 원자적이지 않아서 둘중 1개가 실패하면 데이터 불일치 발생)
- check-modify 패턴으로 쓰면 race condition이 발생할 수 있음

#### 구체적인 시나리오
현재 설계의 흐름: 유저 첫 guess → Redis에 "초기화 완료" 플래그 세팅 → Supabase에 FAIL INSERT

Redis 플래그 세팅 성공 → DB INSERT 실패 시:
1. Redis는 "이미 INSERT 했음"이라고 알고 있음
2. 실제 DB에는 record가 없음
3. 이후 guess에서는 Redis 플래그를 보고 DB write를 스킵함
4. → SUCCESS/GIVEUP 시 UPDATE할 대상 row가 DB에 없음
5. → 잔디밭에도 해당 날짜 기록이 아예 누락됨

#### 왜 이 구조가 된 건지 (배경)
- 매 guess마다 "첫 요청인지" DB를 조회하면 느리니까 Redis 플래그로 캐싱
- 그런데 Redis 플래그와 DB 상태를 원자적으로 같이 쓸 수 없어서 불일치 가능성이 생김

## 고민 (Redis와 DB에 언제 어떻게 저장할까?)
- attempt count은 일단 나중에 고려하고 status만 생각해보자
- Redis에선 퀴즈의 상태를 캐싱해서, GiveUP이나 Correct 이후의 제출 시 count나 DB 쓰기를 방지함
- FAIL 상태는 아직 정답 못맞춘 상태로, 나중에 SUCCESS나 GIVEUP으로 변경될 수 있음

### 방법 1) 동기 우선 + 실패 시 백그라운드 재시도
- 모든 DB write(FAIL/SUCCESS/GIVEUP)를 동기로 시도
- DB 쓰기 실패 시 게임 플로우는 막지 않고, 백그라운드(asyncio task)에서 재시도
- 정상 케이스(99%+)에서는 동기 write 성공 → 즉시 반영, UX 문제 없음
- 실패 케이스만 백그라운드 재시도 → 약간 지연되지만 극히 드문 상황
- 백그라운드 재시도는 in-process(asyncio task)로 충분, 서버 재시작 시 유실 가능하나 극히 드문 케이스의 극히 드문 케이스라 수용 가능
- 추가 고민: Redis 플래그의 역할 재정의 필요 (동기 write 실패 시 플래그를 세팅할지 말지 → 원래 dual write 문제와 연결됨)
- 집계(write) 복잡도가 높음: 동기/비동기 분기, dual write 방어(DB ON CONFLICT 조건), 동시성(INSERT/UPSERT 순서, count 누락) 등 고려 필요
- 조회(read)는 단순: DB만 조회하면 됨

#### 백그라운드 재시도 방식 선택

| | asyncio.create_task | FastAPI BackgroundTasks | arq | Celery |
|---|---|---|---|---|
| 추가 의존성 | 없음 | 없음 | arq 패키지 | celery 패키지 |
| 별도 프로세스 | X | X | O | O |
| 내장 retry | X (직접 구현) | X (직접 구현) | O | O |
| 서버 재시작 시 | 유실 | 유실 | 유지 | 유지 |
| 복잡도 | 최소 | 최소 | 중간 | 높음 |

- FastAPI BackgroundTasks: 응답 반환 후 실행되지만 요청 lifecycle에 묶여 있어 긴 재시도 루프에 부적합
- asyncio.create_task: 요청과 완전히 분리된 fire-and-forget, 재시도 루프를 직접 구현 (sleep + retry)
- arq: Redis를 broker로 사용하는 async 경량 task queue, 내장 retry 지원, 별도 worker 프로세스 필요
- Celery: 풍부한 기능(retry, rate limiting, 모니터링), 별도 worker + broker 필요, 이 규모에서는 오버엔지니어링
- **결론**: 재시도를 위해서라면 DB 장애 자체가 극히 드물고, 재시도까지 가는 건 더 드물고, 서버 재시작과 겹치는 건 더더욱 드물어서 asyncio.create_task가 가장 적합? 만약 모든 쓰기를 비동기로 한다면 arq가 적합할 듯

### 방법 2) Write-Behind + Daily Batch + 조회 시 Redis/DB 혼합

- 게임 중에는 Redis만 write (status, count 등) → DB write 자체가 게임 플로우에 없음
- 하루 1번 배치로 Redis의 stat 데이터를 DB에 flush (Write-Behind 패턴)
- 조회 시 오늘치는 Redis, 과거는 DB에서 읽어 합산
- 장애 격리: DB가 죽어도 게임 + 오늘치 조회 모두 정상 동작
- 집계(write) 복잡도가 가장 낮음: 게임 중 DB write 없음, 배치 1번으로 처리
- 조회(read)는 약간 복잡: 오늘(Redis) + 과거(DB)를 합쳐서 응답
- DB 쓰기 횟수 최소화: 개별 요청마다 UPSERT → 배치 1번

#### 고려사항
- 배치 실행 전 Redis 데이터 유실 시 해당 날짜 stat 영구 누락 → Redis AOF 활성화 + 충분한 TTL로 대응
- 배치 실패 시 재시도 로직 필요
- [ ] TODO: 배치 타이밍 결정 (비즈니스적 고려 필요)

#### 배치 스케줄러 선택

| 방식 | 장점 | 단점 |
|---|---|---|
| **Airflow (기존 인프라)** | 이미 admin API 호출 중, DAG 추가만 하면 됨, 모니터링/재시도 내장 | Airflow 자체가 무거운 인프라 (이미 운영 중이라 추가 비용 없음) |
| **APScheduler (FastAPI 내부)** | 외부 의존성 없음, 배포 단위 동일 | FastAPI 프로세스에 묶임 (재시작 시 스케줄 초기화), 멀티 worker 시 중복 실행 주의 |
| **Linux cron (Oracle 인스턴스)** | 가장 단순, `curl` 한 줄 | 모니터링/재시도 직접 관리, 서버 접속해서 관리 |
| **GitHub Actions (scheduled)** | 서버 부담 없음, 무료 | 외부에서 서버 호출 필요 (보안), 스케줄 정확도 낮음 (수 분 지연 가능) |

- 현재 Airflow가 퀴즈 설정을 위해 admin API를 호출하는 구조가 이미 존재
- FastAPI에 배치용 엔드포인트를 만들고, Airflow DAG를 추가하는 것이 기존 패턴과 동일하여 가장 자연스러움
- **결론**: FastAPI에 배치 엔드포인트를 만들고, 외부에서 API 호출로 배치 실행 (Airflow 사용 가능성 높음)


## 방법 비교

| | 방법 1) 동기 우선 + 백그라운드 재시도 | 방법 2) Write-Behind + Daily Batch |
|---|---|---|
| **DB write 방식** | 동기 시도, 실패 시 백그라운드 재시도 | 게임 중 DB write 없음, 하루 1번 배치 |
| **게임 API latency** | DB write latency 포함 (정상 시) | DB write latency 없음 |
| **집계 흐름 복잡도** | 높음 (동기/비동기 분기, 실패 시 재시도 경로) | 낮음 (Redis write만, 배치는 별도) |
| **Dual Write 문제** | Redis↔DB 불일치 발생 가능 → DB 레벨 방어 필요 | 게임 중 Dual Write 자체가 없음 |
| **동시성 문제** | INSERT/UPSERT 순서, count 누락 등 고려 필요 | 게임 중 DB write 없으므로 해당 없음, 배치는 단독 실행 |
| **조회 복잡도** | 낮음 (DB만 조회) | 중간 (오늘: Redis, 과거: DB를 합쳐서 응답) |
| **UX (잔디 실시간성)** | 동기 write 성공 시 즉시 반영, 실패 시 지연 | 오늘치는 Redis에서 읽으므로 항상 즉시 반영 |
| **DB 장애 시 영향** | 게임 API latency 증가 (동기 write timeout 대기) | 게임 API 영향 없음 (완전 격리) |
| **데이터 유실 리스크** | DB write 실패분만 유실 가능 (백그라운드 재시도로 복구) | 배치 전 Redis 데이터 유실 시 해당 날짜 영구 누락 (AOF + TTL로 대응) |

### 핵심 트레이드오프
- 방법 1: 집계(write) 쪽이 복잡하고 조회(read) 쪽이 단순
- 방법 2: 집계(write) 쪽이 가장 단순하고 조회(read) 쪽이 약간 복잡 (Redis + DB 합산), 배치 인프라 필요

### Stat Redis TTL 정책

- **결론**: 고정 7일 TTL 채택
- OOM 방지 + 배치 실패 시 7일간 재시도 여유
- 조회 시 `end_date`부터 7일 전까지 직접 키 조회 (최대 7개, SCAN 불필요)
- 7일 넘게 배치 실패하면 유실되나, AOF 활성화 + 모니터링으로 대응

### cf. 탈락한 방법) 동기 write + Redis 플래그 상태 관리
- 방법 1의 변형: 동기 write는 같지만, 실패 시 백그라운드 재시도 대신 Redis 플래그 상태로 다음 요청에서 재시도
- Redis 플래그에 pending/confirmed 상태를 둬서 DB 실패 시 다음 요청에서 재시도
  1. 첫 guess/hint → Redis를 `pending`으로 세팅 → DB INSERT 시도
  2. DB 성공 → Redis를 `confirmed`로 변경
  3. DB 실패 → `pending` 상태 유지 → 다음 요청에서 재시도
- **탈락 사유**: Redis 플래그 상태 관리(none/pending/confirmed)가 복잡하고, 방법 1 대비 이점이 없음