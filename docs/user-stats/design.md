# User Stats Design: 유저 통계 집계 및 조회

## 개요

로그인한 유저의 게임 플레이 통계를 저장하고 조회하는 기능. 유저 인증은 `docs/auth-design.md`의 Supabase JWT 기반 인증을 사용한다.
user_quiz_results 테이블를 활용해서
1) 유저들의 퀴즈 푼날/퀴즈를 시도 했지만 못푼 날/포기한 날을 Github의 잔디 심기(Contribution Graph)처럼 시각화하고
2) 연속 정답 일수를 계산해서 보여주고
3) 퀴즈별 통계(ex. 정답률, 평균 시도 횟수)등을 보여줄 계획임 (나중에 docs/quiz-stats-desing.md에서 설계 예정)

## user_quiz_results 테이블 (in Supabase)

### 컬럼
1) id (bigint, Primary Key, auto-increment)
2) user_id (uuid, Foreign Key -> auth.users, ON DELETE CASCADE)
3) quiz_date (date) : 퀴즈 날짜
4) status (text or enum, default 'FAIL') : 'SUCCESS' / 'FAIL'/ 'GIVEUP'
   - 첫 guess 시 FAIL로 INSERT, 이후 SUCCESS 또는 GIVEUP 시 UPDATE
   - record가 없으면 시도 자체를 안 한 것으로 간주 (프론트에서 None 처리)
5) guess_count (int, nullable) : guess 횟수
   - Redis 카운터(user:{user_id}:quiz:{date}:guesses)로 guess마다 증가
   - SUCCESS 시점에만 Redis 카운터 값을 읽어 Supabase에 기록
6) hint_count (int, nullable) : hint 사용 횟수
   - Redis 카운터(user:{user_id}:quiz:{date}:hints)로 hint마다 증가
   - SUCCESS 시점에만 Redis 카운터 값을 읽어 Supabase에 기록
6) updated_at (timestamp, default now()) : 레코드 수정 시각
   - INSERT 시 now()로 설정, SUCCESS/GIVEUP UPDATE 시 갱신

### 고려사항
- quizzes 테이블은 다른 DB에 존재하고, user_quiz_results 테이블만 존재하는 구조
- (user_id, quiz_date)는 무조건 unique 해야함
- 특정 유저의 최근 1년치 날짜 범위 데이터를 긁어오는 일(잔디밭 기능)이 빈번해서 index를 걸어두면 좋을 것 같음
- (나중에 추가할) 퀴즈별 통계를 위해 특정 날짜 데이터를 모두 조회하는 기능은 하루에 1번 정도라 성능 걱정을 크게 안해도 될듯

## 스텟 조회 API / 연속 정답 / outage_dates 테이블
- `docs/user-stats/get-stats.md` 참고

## Supabase DB 접근 방식
- SQLAlchemy (asyncpg) + async engine으로 Supabase PostgreSQL에 직접 연결
  - Supabase SDK 대신 SQLAlchemy를 선택한 이유: Supabase 종속성 제거(이식성), 익숙한 ORM 방식, 복잡한 쿼리 확장성
  - 현재 구조에서 RLS 불필요 (서버에서 인증된 user_id를 WHERE절로 처리)
  - connection pool: `pool_size`를 작게 설정하여 free tier 제한(60개) 대응

## Game API에서 Stat 집계 (Write-Behind + Daily Batch)
- 설계 과정에서 검토한 대안과 비교는 `docs/user-stats/problems.md` 참고
- 게임 중에는 Redis만 write, DB write는 하루 1번 배치로 처리 (Write-Behind 패턴)
- 장애 격리: DB가 죽어도 게임 + 오늘치 조회 모두 정상 동작
- 기존 game API에 `get_optional_user`를 추가하여, 로그인 유저의 경우 Redis에 stat을 기록

### Redis 상태 키
- `user:{user_id}:quiz:{date}:stat` — Hash 자료구조, fields:
  - `status`: `FAIL` / `SUCCESS` / `GIVEUP`
    - 키가 없으면 → 첫 요청
    - `FAIL` → 진행 중
    - `SUCCESS` / `GIVEUP` → 종료됨 (count 증가 안 함)
      - 게임 자체는 SUCCESS/GIVEUP 이후에도 guess 요청을 보낼 수 있지만, stat 관점에서는 종료된 상태이므로 count 불필요
  - `guesses`: guess 횟수 카운터
  - `hints`: hint 사용 횟수 카운터
- Hash를 사용하는 이유: 키 1개로 관리하여 메모리 오버헤드 감소, TTL 관리 단순화 (EXPIRE 1회), HGETALL로 일괄 조회 가능

### 집계 흐름 (게임 중, Redis only — Lua script로 원자적 처리)
- 게임 중 DB write 없음 → Dual Write 문제 해당 없음
- Lua script로 status 확인 + 카운터 증가 + status 변경을 원자적으로 처리 → 동시성 문제 해결
  - Redis는 Lua script 실행 중 다른 명령을 처리하지 않음 (single-threaded)

#### Lua script
```lua
-- KEYS[1] = user:{user_id}:quiz:{date}:stat (Hash)
-- ARGV[1] = result ('SUCCESS', 'GIVEUP', 'WRONG')
-- ARGV[2] = field ('guesses' or 'hints')

local status = redis.call('HGET', KEYS[1], 'status')

-- Terminal state: skip everything
if status == 'SUCCESS' or status == 'GIVEUP' then
    return 0
end

-- INCR counter (auto 0→1 if field doesn't exist)
redis.call('HINCRBY', KEYS[1], ARGV[2], 1)

-- Update status based on result
if ARGV[1] == 'SUCCESS' then
    redis.call('HSET', KEYS[1], 'status', 'SUCCESS')
elseif ARGV[1] == 'GIVEUP' then
    redis.call('HSET', KEYS[1], 'status', 'GIVEUP')
elseif not status then
    -- First request (no status yet) → set FAIL
    redis.call('HSET', KEYS[1], 'status', 'FAIL')
end

return 1
```

#### 흐름 요약
0. **status가 `SUCCESS` / `GIVEUP`** → 전체 스킵 (count 증가 없음)
1. **카운터 증가** → guess면 guesses INCR, hint면 hints INCR (키 없으면 자동 0→1)
2. **정답(SUCCESS)** → status를 `SUCCESS`로 변경
3. **포기(GIVEUP)** → status를 `GIVEUP`으로 변경
4. **첫 guess/hint (오답)** → status를 `FAIL`로 세팅
5. **이후 guess/hint (오답)** → 카운터만 증가, status 변경 없음
6. **이탈(FAIL 유지)** → 추가 처리 없음

### Daily Batch / 데이터 유실 리스크
- `docs/user-stats/daily-batch.md` 참고

### 정합성 검토

#### 1) Dual Write 문제
- 게임 중 DB write가 없으므로 Redis↔DB 불일치 자체가 발생하지 않음 → **완벽히 해결**
- DB write는 배치에서만 발생하며, Redis → DB 단방향 flush이므로 dual write가 아님

#### 2) 동시성 (Race Condition)
- Lua script로 status 확인 + 카운터 증가 + status 변경을 원자적으로 처리 → **완벽히 해결**
- Redis는 single-threaded이므로 Lua script 실행 중 다른 명령이 끼어들 수 없음


### 결정해야될 것
- [ ] 배치 주기, TTL 기간
- [ ] DB Connection Pool
- [ ] register_script 주입?
- [ ] Redis AOF 전략도 재검토
