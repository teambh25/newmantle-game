# User Stats Test Plan

`docs/user-stats/impl-plan.md` Phase 3-6 테스트 계획서.

---

## Phase 3: Lua Script & Redis Stat Recording

### 테스트 대상 범위

| 컴포넌트 | 파일 | 역할 |
|-----------|------|------|
| Lua Scripts | `features/common/redis_scripts.py` | Redis Hash에 대한 원자적 stat 기록 (guess/hint/giveup) |
| StatRepository | `features/stats/repository.py` | Lua script 호출 (Redis 계층) |
| StatService | `features/stats/service.py` | Repository 위임 (thin layer) |
| v2 Game Router | `features/game/v2/routers.py` | stat 기록 호출 + 에러 격리 (try/except) |

### 유닛 테스트 — 해당 없음

Phase 3에는 순수 계산 로직이나 알고리즘이 없다. Lua script의 상태 전이 로직은 Redis 실행 컨텍스트에 의존하므로 mocking으로 검증하면 의미가 없고, 통합 테스트에서 실제 Redis로 검증한다. StatService는 Repository에 단순 위임하는 thin layer이므로 별도 유닛 테스트 불필요.

### 통합 테스트 — Lua Script + StatRepository (Real Redis)

**목적**: Lua script의 상태 전이 명세가 실제 Redis에서 올바르게 동작하는지 검증.

**인프라**: 실제 Redis 인스턴스 (Docker compose의 redis 서비스 또는 테스트용 Redis).

**테스트 대상**: `StatRepository.record_guess / record_hint / record_giveup`을 통해 Lua script 실행 후, Redis Hash의 최종 상태를 검증.

**검증 방식**: `conftest.py`에 `assert_stat(redis_client, user_id, date, *, status, guesses, hints)` 헬퍼 함수를 정의. `HGETALL`로 해당 키의 전체 필드를 조회한 뒤 기대값과 비교. `None`으로 전달된 필드는 검증을 스킵. 모든 필드가 `None`이면 키 자체가 비어있는지 검증.

#### Test Suite 1: Guess Script 상태 전이

| # | 테스트 케이스 | 초기 상태 | 동작 | 기대 결과 |
|---|--------------|-----------|------|-----------|
| 1 | 첫 오답 guess | 키 없음 | `record_guess(is_correct=False)` | `status=FAIL, guesses=1` |
| 2 | 연속 오답 guess | `status=FAIL, guesses=2` | `record_guess(is_correct=False)` | `status=FAIL, guesses=3` |
| 3 | 정답 guess | `status=FAIL, guesses=3` | `record_guess(is_correct=True)` | `status=SUCCESS, guesses=4` |
| 4 | 첫 guess가 정답 | 키 없음 | `record_guess(is_correct=True)` | `status=SUCCESS, guesses=1` |
| 5 | SUCCESS 이후 guess 무시 | `status=SUCCESS, guesses=1` | `record_guess(is_correct=False)` ×2 | 변경 없음 (`status=SUCCESS, guesses=1`) |
| 6 | GIVEUP 이후 guess 무시 | `status=GIVEUP, guesses=1` | `record_guess(is_correct=True)` | 변경 없음 (`status=GIVEUP, guesses=1`) |

#### Test Suite 2: Hint Script 상태 전이

| # | 테스트 케이스 | 초기 상태 | 동작 | 기대 결과 |
|---|--------------|-----------|------|-----------|
| 1 | 첫 hint (상태 없음) | 키 없음 | `record_hint()` | `status=FAIL, hints=1` |
| 2 | 연속 hint | `status=FAIL, hints=1` | `record_hint()` ×2 | `status=FAIL, hints=3` |
| 3 | SUCCESS 이후 hint 무시 | hint×1 → guess(correct) | `record_hint()` | 변경 없음 (`status=SUCCESS, hints=1`) |
| 4 | GIVEUP 이후 hint 무시 | hint×1 → guess(wrong) → giveup | `record_hint()` | 변경 없음 (`status=GIVEUP, hints=1`) |

#### Test Suite 3: Giveup Script 상태 전이

| # | 테스트 케이스 | 초기 상태 | 동작 | 기대 결과 |
|---|--------------|-----------|------|-----------|
| 1 | 진행 중 giveup | guess(wrong) ×3 | `record_giveup()` | `status=GIVEUP` |
| 2 | 첫 요청이 giveup | 키 없음 | `record_giveup()` | `status=GIVEUP` |
| 3 | SUCCESS 이후 giveup 무시 | guess(correct) | `record_giveup()` | 변경 없음 (`status=SUCCESS`) |
| 4 | GIVEUP 이후 중복 giveup 무시 | guess(wrong) → giveup | `record_giveup()` | 변경 없음 (`status=GIVEUP`) |

#### ~~Test Suite 4: TTL 설정~~ (삭제됨 — TTL은 운영 편의 기능으로 비즈니스 로직이 아님)

#### Test Suite 5: 복합 시나리오 (전체 게임 흐름)

| # | 테스트 케이스 | 동작 순서 | 기대 최종 상태 |
|---|--------------|-----------|---------------|
| 1 | 일반 게임: 오답 → 힌트 → 정답 | guess(wrong) → hint → guess(wrong) → guess(correct) | `status=SUCCESS, guesses=3, hints=1` |
| 2 | 포기 게임: 오답 → 포기 | guess(wrong) → guess(wrong) → giveup | `status=GIVEUP, guesses=2` |
| 3 | 포기 후 추가 시도 무시 | guess(wrong) → giveup → guess(correct) → hint | `status=GIVEUP, guesses=1` (giveup 이후 변경 없음) |

#### Test Suite 6: Stat 격리

| # | 테스트 케이스 | 기대 결과 |
|---|--------------|-----------|
| 1 | 다른 유저 격리 | user-A와 user-B가 같은 날짜에 guess → 각각 독립된 Hash에 기록 |
| 2 | 다른 날짜 격리 | 같은 유저가 다른 날짜에 guess → 각각 독립된 Hash에 기록 |

### E2E 테스트 — v2 Game Router + Stat Recording

**목적**: 실제 HTTP 요청 → 게임 응답 + stat 기록이 end-to-end로 올바르게 연결되는지 검증. stat 에러가 게임 응답에 영향을 주지 않는 에러 격리도 검증.

**인프라**: FastAPI TestClient + Real Redis. GameServiceV2는 mock (게임 로직 자체는 이미 별도 테스트 존재).

**Mocking 사용처**:
- `GameServiceV2`: 게임 서비스는 외부 의존성이며, 이미 `test_game_service_v2.py`에서 검증됨. E2E에서는 게임 응답을 고정하고 stat 기록 흐름에 집중.
- `get_optional_user`: JWT 인증은 외부 서비스(Supabase)에 의존하는 부분이므로 mock으로 user_id를 주입.

#### Test Suite 7: 로그인 유저 stat 기록

| # | 테스트 케이스 | 동작 | 기대 결과 |
|---|--------------|------|-----------|
| 1 | guess 성공 시 stat 기록 | `GET /v2/quizzes/{date}/guess/{word}` (user_id 존재, 정답) | 200 응답 + Redis에 `status=SUCCESS, guesses=1` |
| 2 | guess 오답 시 stat 기록 | `GET /v2/quizzes/{date}/guess/{word}` (user_id 존재, 오답) | 200 응답 + Redis에 `status=FAIL, guesses=1` |
| 3 | hint 시 stat 기록 | `GET /v2/quizzes/{date}/hint/{rank}` (user_id 존재) | 200 응답 + Redis에 `hints=1` |
| 4 | give-up 시 stat 기록 | `GET /v2/quizzes/{date}/give-up` (user_id 존재) | 200 응답 + Redis에 `status=GIVEUP` |

#### Test Suite 8: 비로그인 유저 stat 미기록

| # | 테스트 케이스 | 동작 | 기대 결과 |
|---|--------------|------|-----------|
| 1 | 비로그인 guess | `GET /v2/quizzes/{date}/guess/{word}` (user_id=None) | 200 응답 + Redis에 키 없음 |
| 2 | 비로그인 hint | `GET /v2/quizzes/{date}/hint/{rank}` (user_id=None) | 200 응답 + Redis에 키 없음 |
| 3 | 비로그인 give-up | `GET /v2/quizzes/{date}/give-up` (user_id=None) | 200 응답 + Redis에 키 없음 |

#### Test Suite 9: Stat 에러 격리

| # | 테스트 케이스 | 동작 | 기대 결과 |
|---|--------------|------|-----------|
| 1 | Redis 장애 시 guess 정상 | stat_service.record_guess에서 예외 발생 (mock) | 게임 200 응답 정상 반환, stat만 실패 |
| 2 | Redis 장애 시 hint 정상 | stat_service.record_hint에서 예외 발생 (mock) | 게임 200 응답 정상 반환 |
| 3 | Redis 장애 시 give-up 정상 | stat_service.record_giveup에서 예외 발생 (mock) | 게임 200 응답 정상 반환 |

> **Mocking 근거 (Suite 9)**: Redis 장애는 현실에서 억지로 재현하기 힘든 예외 상황이므로 mock으로 예외를 주입한다.

---

## Phase 4: Stats 조회 API

### 테스트 대상 범위

| 컴포넌트 | 파일 | 역할 |
|-----------|------|------|
| calculator | `features/stats/calculator.py` | 순수 계산 함수 (`to_calendar_status`, `calc_current_streak`, `calc_max_streak`) |
| StatService (query) | `features/stats/service.py` | `get_overview`, `get_daily` + 응답 조립 (`_build_calendar`, `_build_summary`) |
| StatRepository (query) | `features/stats/repository.py` | `fetch_stat`, `fetch_recent_stats` (Redis), `fetch_all_results` (DB+Redis merge) |
| Stats Router | `features/stats/routers.py` | `GET /v2/stats`, `GET /v2/stats/{date}` |

### 유닛 테스트 — calculator 순수 함수

**목적**: `calculator.py`의 순수 함수를 외부 의존성 없이 검증. 입력은 Python dict/set → 출력은 계산 결과.

**Mocking**: 없음. 순수 함수이므로 입력 데이터를 직접 구성.

> `_build_calendar`와 `_build_summary`는 단순 조립 로직(필터링/정렬/합산)이므로 별도 유닛 테스트 없이 통합 테스트에서 `get_overview` 응답을 통해 간접 검증.

#### Test Suite 10: `to_calendar_status` 매핑

| # | 테스트 케이스 | 입력 | 기대 결과 |
|---|--------------|------|-----------|
| 1 | 힌트 없이 성공 | `status="SUCCESS", hint_count=0, is_outage=False` | `SUCCESS_WITHOUT_HINT` |
| 2 | 힌트 사용 성공 | `status="SUCCESS", hint_count=2, is_outage=False` | `SUCCESS_WITH_HINT` |
| 3 | 실패 | `status="FAIL", hint_count=0, is_outage=False` | `FAIL` |
| 4 | 포기 | `status="GIVEUP", hint_count=1, is_outage=False` | `FAIL` |
| 5 | 장애일 (성공이어도 OUTAGE) | `status="SUCCESS", hint_count=0, is_outage=True` | `OUTAGE` |

#### Test Suite 11: `calc_current_streak`

| # | 테스트 케이스 | 입력 (end_date 기준) | 기대 결과 |
|---|--------------|---------------------|-----------|
| 1 | end_date가 SUCCESS | 3/13 SUCCESS, 3/12 SUCCESS, 3/11 FAIL | streak=2 |
| 2 | end_date가 FAIL | 3/13 FAIL, 3/12 SUCCESS, 3/11 SUCCESS | streak=2 (전날부터 역산) |
| 3 | end_date에 기록 없음 | 3/13 없음, 3/12 SUCCESS | streak=0 (end_date에 기록 없으면 전날부터, 3/12까지 연속이지만 3/13이 끊김) |
| 4 | 장애일 건너뛰기 | 3/13 SUCCESS, 3/12 outage, 3/11 SUCCESS | streak=2 (3/12 스킵) |
| 5 | 장애일에 SUCCESS 기록 무시 | 3/13 SUCCESS, 3/12 outage+SUCCESS, 3/11 SUCCESS | streak=2 (장애 발생 전 기록 남았음, 공정성을 위해 무시) |
| 6 | 장애일에 FAIL 기록 무시 | 3/13 SUCCESS, 3/12 outage+FAIL, 3/11 SUCCESS | streak=2 (동일) |
| 7 | 장애일에 GIVEUP 기록 무시 | 3/13 SUCCESS, 3/12 outage+GIVEUP, 3/11 SUCCESS | streak=2 (동일) |
| 8 | 하루 gap으로 streak 끊김 | 3/13 SUCCESS, 3/12 기록 없음(outage 아님), 3/11 SUCCESS | streak=1 |
| 9 | outage만 존재, 기록 없음 | result_map 비어있음, 3/11~3/12 outage | streak=0 (outage는 스킵만 할 뿐, SUCCESS 없으면 0) |
| 10 | 빈 result_map | 결과 없음 | streak=0 |
| 11 | 전부 SUCCESS | 3/11~3/13 모두 SUCCESS | streak=3 |

#### Test Suite 12: `calc_max_streak`

| # | 테스트 케이스 | 입력 | 기대 결과 |
|---|--------------|------|-----------|
| 1 | 기록 없고 outage 아닌 날이 streak 끊음 | 3/10 SUCCESS, 3/12 SUCCESS (3/11 기록 없음, outage 아님) | max=1 |
| 2 | 단일 streak | 3/10~3/13 연속 SUCCESS | max=4 |
| 3 | 여러 streak 중 최대값 | 3/10~3/11 SUCCESS, 3/12 FAIL, 3/13~3/16 SUCCESS | max=4 |
| 4 | 장애일이 streak 끊지 않음 | 3/10 SUCCESS, 3/11 outage, 3/12 SUCCESS | max=2 |
| 5 | 장애일에 SUCCESS 기록 무시 | 3/10 SUCCESS, 3/11 outage+SUCCESS, 3/12 SUCCESS | max=2 (장애 발생 전 기록 남았음, 공정성을 위해 무시) |
| 6 | 장애일에 FAIL 기록 무시 | 3/10 SUCCESS, 3/11 outage+FAIL, 3/12 SUCCESS | max=2 (동일) |
| 7 | 장애일에 GIVEUP 기록 무시 | 3/10 SUCCESS, 3/11 outage+GIVEUP, 3/12 SUCCESS | max=2 (동일) |
| 8 | outage만 존재, 기록 없음 | result_map 비어있음, 3/10~3/11 outage | max=0 |
| 9 | 빈 result_map | 결과 없음 | max=0 |
| 10 | 전부 FAIL | FAIL 3회 | max=0 |

---

### 통합 테스트 — StatRepository 조회 (Real Redis)

**목적**: Redis에서 기록된 stat을 `fetch_stat` / `fetch_recent_stats`로 올바르게 읽어오는지 검증. 파싱(필드명 매핑, 기본값 처리)이 올바른지 포함.

**인프라**: 실제 Redis 인스턴스. DB 불필요 (Redis 조회 메서드만 테스트).

**검증 방식**: `redis_client.hset`으로 Redis Hash에 직접 데이터를 구성한 뒤 `fetch_stat` / `fetch_recent_stats`를 호출. Lua script(record 메서드)에 의존하지 않고 파싱 로직만 독립 검증.

#### Test Suite 13: `fetch_stat`

| # | 테스트 케이스 | 사전 조건 (`hset`) | 기대 결과 |
|---|--------------|-----------|-----------|
| 1 | 오답 + 힌트 사용 | `{status: FAIL, guesses: 2, hints: 1}` | `QuizResultEntry(status="FAIL", guess_count=2, hint_count=1)` |
| 2 | 힌트 쓰고 정답 | `{status: SUCCESS, guesses: 3, hints: 2}` | `QuizResultEntry(status="SUCCESS", guess_count=3, hint_count=2)` |
| 3 | 기록 없으면 None | 키 없음 | `None` |
| 4 | 힌트 안 쓰고 정답 (hints 필드 없음) | `{status: SUCCESS, guesses: 1}` | `QuizResultEntry(status="SUCCESS", guess_count=1, hint_count=0)` |
| 5 | 힌트만 사용 (guesses 필드 없음) | `{status: FAIL, hints: 1}` | `QuizResultEntry(status="FAIL", guess_count=0, hint_count=1)` |
| 6 | 첫 요청이 giveup (count 필드 없음) | `{status: GIVEUP}` | `QuizResultEntry(status="GIVEUP", guess_count=0, hint_count=0)` |

#### Test Suite 14: `fetch_recent_stats`

> `fetch_recent_stats`는 `RedisStatKeys.ttl` 기간(현재 7일)만큼의 최근 데이터를 pipeline으로 조회한다. Redis 데이터가 TTL로 자동 만료되므로, 조회 범위를 TTL과 동일하게 맞춰 존재 가능한 모든 데이터를 가져온다.

| # | 테스트 케이스 | 사전 조건 (`hset`) | 기대 결과 |
|---|--------------|-----------|-----------|
| 1 | days 범위만 조회 | day 0 ~ -4 모두 `hset` (days=3) | day 0 ~ -2만 반환 (3건), -3 ~ -4는 무시 |
| 2 | 기록 없음 | 키 없음 | 빈 dict |

### 통합 테스트 — `get_overview` / `get_daily` (Real Redis + Real PostgreSQL)

**목적**: `_build_calendar`, `_build_summary` 조립 로직과 `fetch_all_results`의 DB+Redis merge를 실제 인프라에서 검증.

**인프라**: 실제 Redis + 실제 PostgreSQL. `StatService`에 `StatRepository`(Real Redis + Real DB session)와 `OutageDateRepository`(Real DB session)를 주입.

**검증 방식**: Redis에 `hset`으로 직접 데이터 구성 + DB에 직접 insert → `get_overview` / `get_daily` 호출 후 응답 검증.

#### Test Suite 17: `get_overview` 조립 검증

| # | 테스트 케이스 | 사전 조건 | 기대 결과 |
|---|--------------|-----------|-----------|
| 1 | calendar 기본 동작 | Redis에 3/12 SUCCESS, 3/13 FAIL 기록 | `calendar`에 2건, 각각 `SUCCESS_WITHOUT_HINT`, `FAIL` |
| 2 | calendar에 outage 반영 | 3/11 outage 등록 (기록 없음) | `calendar`에 `OUTAGE` 엔트리 포함 |
| 3 | summary 집계 | SUCCESS 2건 (guesses 합 6, hints 합 2) | `total_success_days=2, avg_guess_when_correct=3.0, avg_hints_when_correct=1.0` |
| 4 | DB+Redis merge (Redis 우선) | DB에 `(user, 3/12, FAIL, 1, 0)`, Redis에 `(3/12, SUCCESS, 5, 2)` | `get_overview` 응답에 3/12가 `SUCCESS_WITHOUT_HINT`로 반영 |
| 5 | 기록 없음 | Redis/DB 모두 비어있음 | `calendar=[], summary.total_success_days=0, streaks=0` |

#### Test Suite 18: `get_daily` 조회

| # | 테스트 케이스 | 사전 조건 | 기대 결과 |
|---|--------------|-----------|-----------|
| 1 | 기록 존재 | Redis에 guess(wrong) 2회 + hint 1회 | `StatDailyResp(date=..., status="FAIL", guess_count=2, hint_count=1)` |
| 2 | 기록 없으면 예외 | 아무 기록 없음 | `StatNotFound` 예외 발생 |

### E2E 테스트 — 해당 없음

Phase 4의 Stats 조회 API는 돈이 오가거나 서비스의 핵심 프로세스가 아닌 읽기 전용 조회이므로 E2E 불필요. 인증(`get_required_user`)은 외부 서비스(Supabase JWT)에 의존하므로 E2E에서 검증하기 부적합하며, 이미 `cores/auth.py` 수준에서 별도 검증 가능.

---

## Phase 5: Outage Date 관리 (Admin)

단순 CRUD (SQLAlchemy `select`/`insert`/`delete` 직접 호출 + thin service wrapper). 자체 로직이 없으므로 별도 테스트 불필요.

---

## Phase 6: Daily Batch (Redis → DB Flush)

### 테스트 대상 범위

| 컴포넌트 | 파일 | 역할 |
|-----------|------|------|
| StatRepository.flush_stats | `features/stats/repository.py` | SCAN → pipeline HGETALL → 파싱 → 청크 단위 DB upsert |
| StatRepository._process_and_upsert_chunk | 동일 | 키 파싱 (user_id 추출, status 검증, 기본값 처리) + upsert |
| StatRepository._upsert_results | 동일 | `INSERT ... ON CONFLICT DO UPDATE` |
| StatService.flush_to_db | `features/stats/service.py` | thin wrapper (repository 위임) |
| Admin Router | `features/admin/routers.py` | `POST /admin/stats/flush` |

### 유닛 테스트 — 해당 없음

파싱 로직(user_id 추출, status 검증, 기본값)이 `_process_and_upsert_chunk` 내부에 Redis pipeline + DB upsert와 결합되어 있어 분리 불가. 통합 테스트에서 검증.

### 통합 테스트 — flush_stats (Real Redis + Real PostgreSQL)

**목적**: Redis에 기록된 stat 데이터가 `flush_stats`를 통해 DB에 올바르게 flush되는지 검증. 파싱, 유효성 검사, 멱등성, 날짜 격리 등.

**인프라**: 실제 Redis + 실제 PostgreSQL. 테스트 전후 양쪽 cleanup 필요.

**사전 조건**: Phase 3 통합 테스트의 `record_guess`/`record_hint`/`record_giveup`으로 Redis에 데이터를 준비한 뒤 flush 실행.

#### Test Suite 15: flush 기본 동작

| # | 테스트 케이스 | 사전 조건 | 동작 | 기대 결과 |
|---|--------------|-----------|------|-----------|
| 1 | 단일 유저 flush | user-A: `{status: FAIL, guesses: 2, hints: 1}` | `flush_stats(date)` | DB에 `(user-A, date, FAIL, 2, 1)` 저장, `flushed=1, skipped=0` |
| 2 | 다수 유저 flush | user-A: SUCCESS, user-B: GIVEUP, user-C: FAIL | `flush_stats(date)` | DB에 3건 저장, `flushed=3, skipped=0` |
| 3 | 빈 Redis | 해당 날짜 기록 없음 | `flush_stats(date)` | `flushed=0, skipped=0` |
| 4 | 멱등성 | user-A 기록 존재 | `flush_stats(date)` 2회 실행 | 2회 모두 동일 결과, DB 데이터 동일 (`ON CONFLICT DO UPDATE`) |
| 5 | 날짜 격리 | date-1과 date-2에 각각 기록 존재 | `flush_stats(date-1)` | date-1만 flush (`flushed=1`), date-2는 DB에 없음 |
| 6 | hints 누락 시 0 기본값 | Redis Hash에 `{status: SUCCESS, guesses: 1}` | `flush_stats(date)` | DB에 `hint_count=0` |
| 7 | guesses 누락 시 0 기본값 | Redis Hash에 `{status: FAIL, hints: 1}` | `flush_stats(date)` | DB에 `guess_count=0` |
| 8 | DB에 이전 기록 존재 시 덮어쓰기 | DB에 `(user-A, date, FAIL, 1, 0)`, Redis에 `SUCCESS, 5, 2` | `flush_stats(date)` | DB가 `(user-A, date, SUCCESS, 5, 2)`로 갱신 |

### E2E 테스트 — 해당 없음

배치 API는 Airflow에서 호출하는 운영 도구. 핵심 프로세스가 아니며, 멱등성으로 재실행 안전. Admin Basic Auth는 기존 패턴과 동일하므로 별도 E2E 불필요.

---

## 파일 구조

```
tests/
├── unit/
│   └── stats/
│       ├── conftest.py              # result_map / outage_dates fixture 팩토리
│       └── test_calculator.py       # Suite 10-12 (calculator.py 순수 함수)
├── integration/
│   └── stats/
│       ├── conftest.py              # Real Redis fixture, cleanup, assert_stat helper
│       ├── test_stat_recording.py   # Suite 1-3, 5-6 (stat recording + key pattern)
│       ├── test_stat_query.py       # Suite 13-14 (Redis 조회)
│       ├── test_stat_overview.py    # Suite 17-17 (get_overview/get_daily, Real Redis + Real DB)
│       └── test_flush.py            # Suite 15 (Redis → DB flush)
└── e2e/
    └── stats/
        ├── conftest.py              # TestClient + mock GameServiceV2 + mock auth
        └── test_v2_stat_recording.py  # Suite 7-9
```

---

## 테스트 인프라 참고사항

- **Real Redis**: Docker compose의 redis 서비스를 활용하거나, 테스트 전용 Redis 인스턴스 사용
- **테스트 격리**: 각 테스트 전에 해당 키를 `DELETE`하여 격리. `FLUSHDB`는 다른 테스트 데이터에 영향을 줄 수 있으므로 지양
- **DB 불필요 (Phase 3, Suite 13-14)**: stat 기록 및 Redis 조회 테스트는 Redis-only. `StatRepository` 생성 시 `session`은 dummy/None으로 처리 가능
- **DB 필요 (Suite 15-18)**: flush, `get_overview`/`get_daily` 테스트는 Real Redis + Real PostgreSQL 모두 필요. 테스트 전후 `user_quiz_results` 테이블 cleanup. `AsyncSession`을 직접 생성하여 `StatRepository`에 주입
- **decode_responses**: conftest의 Redis client는 `decode_responses=True`로 통일. Phase 3 `assert_stat`과 Phase 4 조회 메서드(`fetch_stat` 등) 모두 string 비교
