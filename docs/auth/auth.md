# Auth Design: Supabase JWT 기반 유저 인증

## 개요

프론트엔드에서 Supabase Auth (Google OAuth 2.0)로 로그인 후 발급받은 JWT를 API 요청 시 `Authorization: Bearer <token>` 헤더로 전달한다. 백엔드는 이 토큰을 검증하여 유저를 식별한다.

## 인증 흐름

```
[프론트] Google OAuth -> Supabase Auth -> JWT 발급
                                            |
[프론트] API 요청 (Authorization: Bearer <jwt>) -> [FastAPI] JWT 검증 -> 유저 식별
```

1. 프론트엔드가 Supabase Auth를 통해 Google 로그인 수행
2. Supabase가 JWT (access_token) 발급
3. 프론트엔드가 API 요청 시 `Authorization: Bearer <token>` 헤더에 JWT 포함
4. FastAPI에서 Supabase JWT를 검증하고 유저 정보(sub = user_id) 추출

## JWT 검증 방식
JWKS 대신 Supabase 프로젝트의 `JWT Secret`을 환경변수로 주입하고 HS256으로 직접 검증. 

### 검증 항목
| 항목 | 값 |
|------|-----|
| Algorithm | HS256 |
| Secret | `SUPABASE_JWT_SECRET` (환경변수) |
| Issuer (`iss`) | `https://<project-ref>.supabase.co/auth/v1` |
| Audience (`aud`) | `authenticated` |
| Expiry (`exp`) | 현재 시각 이전이면 거부 |

## Dependency 설계

기존 패턴(`Depends()` 체인)을 따라 두 가지 dependency를 추가한다.

### 1. `get_optional_user` — 선택적 인증

기존 game API(guess, give-up 등)에 적용.
- 토큰 없음 → `None` (비로그인 허용)
- 토큰 유효 → `user_id` 반환
- 토큰 만료 → 401 (`"Token has expired. Please log in again"`)
- 토큰 무효 → 401 (`"Invalid token"`)

### 2. `get_required_user` — 필수 인증

로그인 필수 API에 적용.
- 헤더 없음 → 401 (`"Authorization header required"`)
- 토큰 만료 → 401 (`"Token has expired. Please log in again"`)
- 토큰 무효 → 401 (`"Invalid token"`)

### 구현 참고

- `HTTPBearer(auto_error=False)`를 두 dependency가 공유. `auto_error=True`를 쓰면 FastAPI가 403을 반환하여 커스텀 401 응답을 제어할 수 없기 때문.
- `verify_supabase_jwt`에서 `ExpiredSignatureError`와 `PyJWTError`를 구분하여 만료/무효 에러 메시지를 분리.

## 구현 완료

- [x] `cores/config.py` — `supabase_jwt_secret: str` 필드 추가
- [x] `cores/auth.py` — `verify_supabase_jwt`, `get_optional_user`, `get_required_user` 추가
- [x] `requirements.txt` — `PyJWT` 추가
- [x] `features/game/v2/routers.py` — guess, hint, give-up 엔드포인트에 `get_optional_user` 적용
- [ ] `.env` — `SUPABASE_JWT_SECRET` 값 설정 필요

> **Note**: 유저 stat 집계/조회 관련 설계는 `docs/user-stats/design.md`를 참고한다.

## 기존 API 영향도

- **game API (v1)**: 현재 프로덕션에서 사용중이라 수정하지 말 것!
- **game API (v2)**: 변경 없이 동작. 인증은 선택적(`get_optional_user`)이므로 비로그인 유저도 기존과 동일하게 플레이 가능.
- **admin API**: 기존 HTTP Basic Auth 그대로 유지. 변경 없음.