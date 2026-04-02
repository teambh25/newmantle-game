# User Stats Implementation Plan

`docs/user-stats/design.md` 기반 구현 계획서.

---

## 기존 API 영향도 분석

| 영향 범위 | 상세 | 위험도 |
|-----------|------|--------|
| v1 game API | 변경 없음. v1 router/service 수정하지 않음 | 없음 |
| v2 game API | router에서 Lua script 호출 추가. **GameServiceV2 자체는 변경 없음** | 낮음 |
| Admin API | outage_dates CRUD 추가, 배치 엔드포인트 추가 | 낮음 |
| Redis | 기존 키 패턴 변경 없음. `user:{user_id}:quiz:{date}:stat` Hash 키 추가 (fields: status, guesses, hints) | 없음 |
| Docker | PostgreSQL 연결을 위한 환경변수 추가. 기존 서비스 변경 없음 | 없음 |
| 기존 테스트 | v2 router 테스트에 StatService mock 주입 필요 (기존 테스트 수정) | 낮음 |

> v2 router에 StatService 호출을 추가하지만, `user_id`가 None이면 stat 로직을 skip하므로 비로그인 유저의 기존 동작은 100% 동일.

---

## 결정 사항

- **DB 연결**: SQLAlchemy + asyncpg
- **DB 엔진 생명주기**: lifespan에서 관리 (Redis pool과 동일 패턴)
- **Lua script 관리**: `features/stats/scripts.py`에 Python 문자열 상수로 정의 (`register_script()` → EVALSHA). 역할별 3개 분리 (guess/hint/giveup)
- **stat 에러 처리**: 에러 무시 (try/except + 로깅). DB 장애 시 스케줄러 재시도 및 알림으로 대응하고, 게임 진행은 중단하지 않음
- **배치 인증**: Admin Basic Auth (기존 패턴). 추후 보안 강화 시 API Key 또는 DB/Supabase Auth로 전환 검토

---

## 구현 순서

### Phase 1: 인프라 (DB 연결 기반) — ✅ 구현 완료

**1-1. 의존성 추가**
- `requirements.txt`에 `sqlalchemy[asyncio]`, `asyncpg` 추가

**1-2. 환경변수 추가**
- `cores/config.py`에 `database_url`, `db_pool_size`, `db_max_overflow` 추가
- `.env.example`에 `DATABASE_URL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` 추가

**1-3. DB 엔진 설정**
- `cores/database.py` 생성: `create_db_engine()`, `create_session_factory()`

**1-4. lifespan에 DB 엔진 추가**
- `cores/event.py` 수정: engine + session_factory lifecycle 추가

**1-5. DB session dependency 추가**
- `dependencies/database.py` 생성: `get_db_session`

---

### Phase 2: 데이터 모델 & Repository — ✅ 구현 완료

**2-1. SQLAlchemy 모델 수정**
- `features/stats/models.py`
  - `UserQuizResult`: `attempt_count` → `guess_count` 변경, `hint_count` 컬럼 추가
  - 나머지 유지 (id: bigint, user_id, quiz_date, status: enum, updated_at, UniqueConstraint)

**2-2. StatRepository 수정**
- `features/stats/repository.py`
  - `insert_first_attempt` 제거 (게임 중 DB write 없음)
  - `update_result` 제거
  - `upsert_results(results: list)` 추가 → 배치용 `INSERT ... ON CONFLICT DO UPDATE`
  - `fetch_results_by_range` 유지
  - `fetch_outage_dates` / `insert_outage_date` / `delete_outage_date` 유지

---

### Phase 3: Lua Script & Redis 집계 — ✅ 구현 완료

**3-1. Redis 키 패턴 변경**
- `cores/redis.py`의 `RedisStatKeys` 수정
  - Hash 1개: `user:{user_id}:quiz:{date}:stat` (fields: `status`, `guesses`, `hints`)

**3-2. Lua script 구현**
- `features/stats/scripts.py`에 역할별 3개 script 분리
  - `RECORD_GUESS_SCRIPT`: ARGV[1]=result(SUCCESS/WRONG) → guesses 증가 + status 변경
  - `RECORD_HINT_SCRIPT`: 인자 없음 → hints 증가만 (status는 FAIL 초기화만)
  - `RECORD_GIVEUP_SCRIPT`: 인자 없음 → status를 GIVEUP으로 변경 (카운터 증가 없음)
  - 필드명은 script 내부 리터럴로 고정
  - 공통: terminal state(SUCCESS/GIVEUP) 시 스킵 → `0` 반환, 처리 시 `1` 반환

**3-3. StatService 재구현**
- `features/stats/service.py` — 게임 중 Redis-only로 변경
  - `record_guess(user_id, quiz_date, is_correct)` → guess script 호출
  - `record_hint(user_id, quiz_date)` → hint script 호출
  - `record_giveup(user_id, quiz_date)` → giveup script 호출
  - stat 조회 로직은 Phase 4에서 구현 예정

**3-4. v2 game router 수정**
- `guess`: `stat_service.record_guess(user_id, date, resp.correct)` 호출
- `hint`: `stat_service.record_hint(user_id, date)` 호출 추가
- `give-up`: `stat_service.record_giveup(user_id, date)` 호출
- stat 호출은 try/except + 로깅으로 감싸 게임 응답에 영향 없도록 처리

---

### Phase 4: Stats 조회 API

`docs/user-stats/get-stats.md` 참고

### Phase 5: Outage Date 관리 (Admin)
`docs/user-stats/outage-dates.md` 참고

### Phase 6: Daily Batch (Redis → DB flush)
`docs/user-stats/daily-batch.md` 참고

### Phase 7: 테스트
`docs/user-stats/test-plan.md` 참고

## 파일 변경/생성 요약

| 구분 | 파일 | 변경 내용 |
|------|------|-----------|
| 수정 | `requirements.txt` | ✅ sqlalchemy[asyncio], asyncpg 추가 |
| 수정 | `cores/config.py` | ✅ database_url, db_pool_size, db_max_overflow 추가 |
| 수정 | `cores/event.py` | ✅ DB engine + session_factory lifecycle 추가 |
| 수정 | `.env.example` | ✅ DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW 추가 |
| 수정 | `cores/redis.py` | ✅ RedisStatKeys를 Hash 1개 키 + fields로 변경 |
| 수정 | `features/game/v2/routers.py` | ✅ StatService 호출 (guess/hint/giveup) + try/except 에러 처리 |
| 수정 | `dependencies/__init__.py` | ✅ get_stat_service export 추가 |
| 수정 | `main.py` | Stats router 등록 |
| 수정 | `features/stats/models.py` | ✅ attempt_count → guess_count, hint_count 추가 |
| 수정 | `features/stats/repository.py` | ✅ insert_first_attempt/update_result 제거, upsert_results 추가 |
| 수정 | `features/stats/service.py` | ✅ Write-Behind 방식으로 전면 재구현 (조회 메서드는 Phase 4) |
| 수정 | `dependencies/stats.py` | ✅ get_stat_service dependency |
| 생성 | `cores/database.py` | ✅ create_db_engine, create_session_factory |
| 생성 | `dependencies/database.py` | ✅ get_db_session dependency |
| 생성 | `features/stats/scripts.py` | ✅ Lua script 3개 (guess/hint/giveup) |
| 생성 | `features/stats/routers.py` | Stats 조회 API + 배치 엔드포인트 |
| 생성 | `schemas/stats.py` | Stats 응답 스키마 |
| 생성 | `tests/unit/stats/` | StatService, StatRepository 테스트 |
