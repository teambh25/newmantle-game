# 게스트 스탯 설계 문서

> 비로그인 유저의 스탯 집계, 공개 조회, 로그인 시 데이터 연동 기능 설계

## 1. 개요

현재 뉴맨틀 게임은 구글 로그인한 유저만 스탯(시도 수, 힌트 수, 성공/실패 등)을 기록하고 조회할 수 있다. 비로그인 유저는 게임은 플레이할 수 있지만 기록이 남지 않아, 이후 가입하더라도 이전 플레이 이력이 유실된다.

이 설계는 비로그인 유저에게도 게스트 ID를 부여하여 스탯을 기록하고, 로그인 시 해당 기록을 회원 계정에 연동할 수 있도록 한다. 또한 스탯 공개 조회 API를 게스트/회원 모두 지원하도록 확장한다.

### 제약 사항

- 기존 아키텍처(FastAPI + Redis + PostgreSQL) 유지
- 인증: Supabase JWT 기반 Google OAuth 구현 완료
- 게스트 스탯은 최대 7일치만 유지 (Redis TTL 자연 만료, DB flush 안 함)
- 잔디(overview/calendar)는 로그인 유저 전용
- v1 엔드포인트는 수정하지 않음

## 2. 요구사항

### 기능 요구사항

- 비로그인 유저도 게스트 ID 기반으로 스탯이 기록되어야 한다
- 비로그인 유저도 스탯 공개 조회 API를 사용할 수 있어야 한다
- 최초 구글 회원가입 시 게스트 스탯을 회원 계정에 1회 연동할 수 있어야 한다
- 잔디(개인 통계 overview)는 로그인 유저만 조회 가능하다
- 게스트 ID도 회원 ID도 없는 완전 미인증 요청은 게임 API 사용 불가(401)

### 비기능 요구사항

- 게스트 스탯은 Redis TTL(7일)로 자동 만료, DB flush 대상에서 제외
- 스탯 기록은 기존과 동일하게 best-effort (실패해도 게임 응답에 영향 없음)
- 매핑 API는 멱등성 불필요 (1회 제한이므로 재호출 시 거부)

## 3. 기술 결정

### 3-1. 게스트 ID 생성: 클라이언트 생성 + UUID 검증 - 서버에서 구현할 건 없음

- **선택**: 브라우저에서 UUID v4 생성, localStorage 저장, 요청마다 서버에 전송
- **검증**: 서버에서 FastAPI의 UUID 타입 검증으로 유효성 확인
- **근거**: 유저 식별용 임시 ID이므로 엄밀한 보안(서버 발급, JWT 등)은 불필요. FastAPI 내장 UUID validation으로 포맷 검증 및 악의적 입력 방어
- **기각된 대안**:
  - 서버 생성: 별도 발급 엔드포인트 필요, 과한 복잡도
  - 문자열 길이만 검증: FastAPI UUID validation도 한 줄이라 복잡도 차이 없음

### 3-2. 게스트 ID 전달 방식: 통합 인증 의존성

- **선택**: 기존 `get_optional_user`를 폐기하고 `get_user_identity`로 대체
  - JWT 있으면 → user_id 반환
  - JWT 없으면 → `X-Guest-Id` 헤더에서 guest_id 추출
  - 둘 다 없으면 → 401
- **근거**: 게스트 ID 도입으로 완전 미인증 상태는 불필요. 서비스 레이어가 기존에 `user_id: str | None`을 받고 있어서 동일 경로로 흘려보내면 하위 레이어 변경 최소화
- **기각된 대안**:
  - 쿼리 파라미터: URL에 ID 노출(로그/캐시), 엔드포인트 시그니처 변경 필요
  - 별도 게스트 API: 게임 엔드포인트 2벌 유지, 코드 중복

### 3-3. 게스트→회원 매핑 트리거: 별도 API

- **선택**: 클라이언트가 로그인 후 `POST /v2/stats/link`를 호출. 게스트 플레이 기록이 있는 상태에서 구글 로그인 시 자동 호출
- **실패 처리**: TODO — Redis 장애 시 재시도 전략 결정 필요 (클라이언트 지수 백오프, 서버 내부 재시도 등)
- **근거**: 디버깅 용이, 응답으로 매핑 결과 확인 가능. 매핑 로직이 멱등하므로 재시도 안전
- **기각된 대안**:
  - 자동 매핑(첫 요청 시): 매핑 실패 시 사용자 인지 어려움, 인증 미들웨어에 비즈니스 로직 혼입

### 3-4. 게스트→회원 매핑 구현: RENAME + 충돌 시 스킵 (Lua 원자화)

- **선택**: 오늘 기준 7일간 순회하며 날짜별로 Lua 스크립트 1회 호출 — EXISTS → (회원 키 있으면 DEL, 없으면 RENAME)을 원자적으로 처리
- **근거**: 최대 7번의 Lua 호출로 SCAN 없이 처리. 동일 날짜 충돌 시 로그인 기록(DB flush 대상)을 우선. Lua 스크립트로 EXISTS→RENAME/DEL을 원자화하여 TOCTOU 경쟁 조건 방지 — 회원 키 EXISTS 체크 자체가 멱등성을 보장
- **기각된 대안**:
  - Redis RENAME만: 동일 날짜 회원 데이터 덮어쓸 위험
  - 머지 후 삭제: 필드 단위 병합이 필요해 Lua 스크립트가 더 복잡해지고, 충돌 시 어느 값을 우선할지 정책 결정 필요

### 3-5. 스탯 공개 조회 식별자: 경로에 유저 타입 포함

- **선택**: `GET /v2/stats/{user_type}/{uuid}/{date}` — `user_type`은 `guest` | `user` enum
- **근거**: URL에 타입이 명시되어 Redis 키 조회가 명확하고, 핸들러 1개로 prefix만 분기
- **기각된 대안**:
  - URL에 `guest:` prefix 포함: injection 공격 위험
  - 양쪽 다 조회: 불필요한 2회 Redis 조회
  - 쿼리 파라미터: 기본값 모호, 공유 URL에서 파라미터 누락 위험

## 4. 아키텍처

### 인증 흐름

```
요청 도착
  │
  ├─ Authorization 헤더 있음 → JWT 검증 → user_id 반환
  │
  ├─ X-Guest-Id 헤더 있음 → UUID 검증 → guest_id 반환
  │
  └─ 둘 다 없음 → 401 Unauthorized
```

### 의존성 구조

```
게임 엔드포인트 (guess, hint, give-up)
  └─ get_user_identity (신규) → user_id 또는 guest_id

스탯 overview (잔디)
  └─ get_current_user (기존) → user_id (JWT 필수)

스탯 공개 조회
  └─ user_type path param → prefix 분기

매핑 API
  └─ get_current_user (기존) → user_id (JWT 필수)
```

### 매핑 흐름

```
POST /v2/stats/link (JWT 필수, body: guest_id)
  │
  └─ 7일 순회 (date = today ~ today-6):
       │
       └─ Lua 스크립트 (LINK_GUEST_STAT_SCRIPT) — 원자적 실행:
            │
            ├─ guest key 없음 → skip (return 0)
            │
            ├─ user key 존재 → guest key DEL (return 1)
            │
            └─ user key 없음 → guest key RENAME → user key (return 2)
```

## 5. 데이터 모델

### Redis 키 패턴

| 키 패턴 | 타입 | 용도 | TTL |
|---------|------|------|-----|
| `user:{uuid}:quiz:{date}:stat` | Hash | 회원 일별 스탯 (status, guesses, hints) | 7일 |
| `guest:{uuid}:quiz:{date}:stat` | Hash | 게스트 일별 스탯 (동일 필드) | 7일 |

### flush 정책

- flush 대상: `user:*:quiz:{date}:stat` 패턴만 (기존과 동일)
- `guest:*` 키는 flush 대상 제외, TTL로 자연 만료

## 6. API 설계

### 변경되는 엔드포인트

| 엔드포인트 | 변경 내용 |
|-----------|----------|
| `GET /v2/quizzes/{date}/guess/{word}` | `get_optional_user` → `get_user_identity` (JWT 또는 guest_id 필수) |
| `GET /v2/quizzes/{date}/hint/{rank}` | 동일 |
| `GET /v2/quizzes/{date}/give-up` | 동일 |
| `GET /v2/stats/{user_id}/{date}` | `GET /v2/stats/{user_type}/{uuid}/{date}`로 변경 |

### 신규 엔드포인트

#### `POST /v2/stats/link`

게스트 스탯을 회원 계정에 연동한다.

- **인증**: JWT 필수 (`get_current_user`)
- **Request Body**: `{ "guest_id": "string" }`
- **Response 204**: No Content

### 변경 없는 엔드포인트

| 엔드포인트 | 비고 |
|-----------|------|
| `GET /v2/stats` (overview/잔디) | `get_current_user` 유지, 로그인 전용 |
| `POST /admin/stats/flush` | `user:*` 패턴만 대상, 게스트 키 자동 제외 |

## 7. 구현 계획

1. **Redis 키 패턴 추가** — `redis_keys.py`에 게스트용 키 생성 함수 추가
2. **통합 인증 의존성** — `get_user_identity` 구현, CORS에 `X-Guest-Id` 헤더 추가
3. **게임 엔드포인트 수정** — `get_optional_user` → `get_user_identity` 교체, 서비스/리포지토리에서 identity 타입에 따라 키 prefix 분기
4. **스탯 공개 조회 API 변경** — `{user_type}/{uuid}/{date}` 경로로 변경
5. **매핑 API 추가** — `POST /v2/stats/link` 엔드포인트 및 매핑 로직 구현
6. **테스트** — 인증 의존성, 게스트 스탯 기록/조회, 매핑(성공/충돌/중복 거부), flush 제외 확인
