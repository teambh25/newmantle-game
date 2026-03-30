# 요약 (중요도 순)

| 중요도 | 섹션 | 항목 | 핵심 내용 |
|--------|------|------|-----------|
| ~~�� High~~ | ~~Game #3~~ | ~~bare `except Exception`~~ | ~~해결: repo→StatRecordError 변환, service에서 best-effort catch~~ |
| **🟢 Low** | Admin #1 | exception handler 미활용 | 코드 중복이지만 동작 문제 없음, 현재 규모에선 유지 |
| ~~🟡 Medium~~ | ~~Admin #3~~ | ~~`KEYS *` 사용~~ | ~~해결: `quiz:index` Set 인덱스로 교체, lazy cleanup으로 TTL 만료 키 정리~~ |
| ~~🟡 Medium~~ | ~~Admin #7~~ | ~~delete_quiz 비원자적 삭제~~ | ~~해결: pipeline+transaction으로 원자적 삭제 + 인덱스 정리~~ |
| ~~🟡 Medium~~ | ~~Game #2~~ | ~~stat_service 관심사 혼재~~ | ~~해결: user_id null check를 stat_service 내부로 이동, 라우터에서 조건 분기 제거~~ |
| ~~🟡 Medium~~ | ~~체크리스트~~ | ~~config 주입 비일관~~ | ~~해당 없음: 싱글턴 config이므로 DI 실익 없음. 순수 로직 클래스(QuizBuilder, Validator)는 생성자 주입이 테스트에 유리하여 현재 상태 유지~~ |
| **🟢 Low** | Admin #2 | Validator.today 고정 | 싱글턴 전환 시에만 문제, 현재는 안전 |
| **🟢 Low** | Admin #4 | fetch_all_answers tuple 반환 | repo-service 간 암묵적 결합 |
| **🟢 Low** | Admin #5 | read_all_answers response_model 없음 | API 문서/응답 검증 누락 |
| **🟢 Low** | Admin #6 | 성공 응답 형태 비일관 | 엔드포인트별 응답 구조 불통일 |
| **🟢 Low** | Admin #8 | extract_date bytes 미처리 | Redis 설정에 따라 bytes 반환 가능 |
| **🟢 Low** | Game #1 | v1/v2 역직렬화 중복 | v1 고정이라 당장 수정 불가 |
| **🟢 Low** | Game #4 | `adpter.py` 오타 | adapter.py가 올바른 철자 |
| **🟢 Low** | Game #5 | v1 response_model 없음 | v1 고정 정책상 변경 안 함 |
| **🟢 Low** | Game #6 | give_up 반환 타입 불일치 | Answer vs GiveUpResp 의미적 불일치 |
| **🟢 Low** | Game #7 | guess dict 이중 변환 | 처음부터 Pydantic 모델 생성이 나음 |
| **🟢 Low** | Game #8 | guess 추가 Redis 호출 | 정답 시 불필요한 RTT, 현재 규모에선 무시 가능 |
| **🟢 Low** | Game #9 | configs.max_rank 직접 참조 | config 주입 비일관 이슈와 동일 |
| ~~🔴 High~~ | ~~Stats #1~~ | ~~`get_stats_daily` 인증 누락~~ | ~~해당 없음: 비로그인 상태에서도 타인 stat 조회 가능은 의도된 설계~~ |
| ~~🟡 Medium~~ | ~~Stats #2~~ | ~~`fetch_all_results` 전체 조회~~ | ~~해당 없음: 유저당 하루 1row, WHERE user_id 조건이라 유저별 최대 ~1,095 row 수준. streak 계산에 start_date 이전 데이터도 필요하여 date range 필터 불필요~~ |
| ~~🟡 Medium~~ | ~~Stats #3~~ | ~~`flush_stats` 청크별 commit~~ | ~~해당 없음: upsert로 멱등성 보장, 부분 flush 후 재실행해도 정합성 유지. 단일 트랜잭션은 락 범위 증가·롤백 비용이 더 큼~~ |
| ~~🟡 Medium~~ | ~~Stats #4~~ | ~~`get_overview` date range 미검증~~ | ~~해결: service에서 start_date > end_date 검증 추가, InvalidDateRange 예외 신설~~ |
| **🟢 Low** | Stats #5 | `StatDailyResp.status`가 str | enum 대신 raw string, API 문서/타입 안전성 저하 |
| **🟢 Low** | Stats #6 | `key.split(":")[1]` 파싱 | 키 포맷에 암묵적 의존, RedisStatKeys에 파싱 메서드 권장 |
| **🟢 Low** | Stats #7 | Lua script 반환값 미사용 | 0/1 반환하지만 caller에서 무시 |
| **🟢 Low** | 체크리스트 | base model 위치 | stats/models.py에 위치 |
| **🟢 Low** | 체크리스트 | graceful shutdown | 필요 여부 검토 |

---

# 내가 찾은 것
- [x] Admin Router에서 stat service를 써야되서 대대적인 코드 구조 개편이 필요할듯?
      => 지금 규모에선 유지하자..
- [x] GameRepo, Admin Repo로 분리하기엔 어색하다? => 괜찮다, 굳이 고민하자면 outageDataService정도 인데 지금처러 간단히 유지하는 것도 괜찮음

- [ ] base model이 app/features/stats/models.py에 있음 — 🟢 Low
- [x] 어디는 config를 주입하고, 어디는 config을 그대로 써서 통일 필요해보임 — 🟡 Medium
      => 싱글턴 config이라 DI 실익 없음. 순수 로직 클래스는 생성자 주입이 테스트에 유리하므로 현재 상태 유지
- [ ] graceful shutdown이 없어도 되나? — 🟢 Low

---

# Admin API 리뷰

## 1. 🟢 Router에서 직접 try/except + HTTPException 변환 — exception handler 미활용
- `admin/routers.py`의 모든 엔드포인트가 `BaseAppException`을 직접 catch해서 `HTTPException`으로 변환하고 있음
- 이미 `exceptions/handlers.py`에 global exception handler 패턴이 있으므로, admin 전용 exception handler를 등록하면 라우터 코드가 훨씬 깔끔해짐
- game 라우터도 동일한 패턴이라 프로젝트 전체적으로 개선 가능
- 예: `BaseAppException` 하위 클래스에 `status_code` 속성을 두고, 하나의 handler로 통합

## 2. 🟢 Validator.today가 생성 시점에 고정됨
- `Validator(today, max_rank)`에서 `today`가 DI 시점의 값으로 고정
- 현재는 요청마다 DI가 새로 생성되므로 문제 없지만, 만약 서비스가 싱글턴으로 바뀌면 날짜가 고정되는 버그 발생 가능
- 의도를 명확히 하려면 `validate_quiz(quiz, today)` 처럼 메서드 파라미터로 받는 게 더 안전

## 3. ~~🟡 `fetch_all_answers`에서 `KEYS *answers` 사용~~ ✅ 해결
- ~~`repository.py:20` — `self.rd.keys("*answers")`는 Redis `KEYS` 명령 사용~~
- **해결**: `quiz:index` Redis Set을 인덱스로 도입. `SMEMBERS` + `MGET`으로 조회, TTL 만료된 stale 키는 lazy cleanup으로 `SREM` 처리

## 4. 🟢 `fetch_all_answers` 반환값이 tuple (answer_keys, answers)
- repo가 두 개의 리스트를 tuple로 반환 → service에서 `zip`으로 조합
- 데이터 구조가 repo와 service 사이에 암묵적으로 결합됨
- `list[dict]`나 DTO로 반환하면 더 명확

## 5. 🟢 `read_all_answers` 응답에 response_model이 없음
- `routers.py:33` — `read_all_answers`는 `response_model` 없이 dict를 직접 반환
- 다른 엔드포인트(`get_outage_dates`)는 `response_model`을 명시하고 있어 비일관적
- API 문서 자동생성과 응답 검증을 위해 response_model 추가 권장

## 6. 🟢 `upsert_quiz` 성공 시 응답 형태 비일관
- `upsert_quiz` → `{date: answer}`, `create_outage_date` → `{"date": date}`, `delete_answer` → `None`
- 성공 응답 형태를 통일하면 클라이언트 측 처리가 간결해짐

## 7. ~~🟡 `delete_quiz`의 검증 로직이 분산됨~~ ✅ 해결
- ~~삭제 후에 `validate_deleted_cnt`로 결과를 검증하는 방식 → 부분 삭제 시 이미 데이터가 일부 날아간 상태~~
- **해결**: pipeline+transaction으로 원자적 삭제 + `quiz:index`에서 `SREM`으로 인덱스 정리

## 8. 🟢 `extract_date`가 bytes를 처리하지 않음
- `RedisQuizKeys.extract_date(key)` — Redis에서 반환된 key가 `bytes`일 수 있음 (`decode_responses=False`인 경우)
- 현재 Redis 클라이언트 설정에 따라 다르지만, 방어 코드가 없음

---

# Game API 리뷰

## 1. 🟢 v1과 v2 서비스 간 역직렬화 로직 중복
- `v1/service.py:55-62` — `_extract_score_and_rank`, `_extract_word_and_score`를 static method로 직접 구현
- `v2/service.py:28,41` — 동일한 역할을 `RedisQuizData.deserialize_*`로 호출
- v1은 수정 불가(프로덕션)이므로 당장 고칠 순 없지만, 같은 로직이 두 곳에 존재한다는 점 인지 필요

## 2. ~~🟡 v2 라우터가 stat_service를 직접 호출 — 관심사 혼재~~ ✅ 해결
- ~~`v2/routers.py` — guess, hint, give_up 모두 `stat_service`를 DI 받아 라우터 레벨에서 `if user_id:` 조건 분기 후 호출~~
- **해결**: `stat_service.record_*` 메서드가 `user_id: str | None`을 받아 내부에서 null check, 라우터의 조건 분기 제거

## 3. ~~��� stat 기록 실��� 시 bare `except Exception` — 에러가 묻힘~~ ✅ 해결
- ~~`v2/routers.py:42-43,69-70,98-99` — `except Exception`으로 모든 ��외를 삼키고 warning만 남김~~
- **해결**: repo에서 `redis.RedisError` → `StatRecordError`로 변환, service에서 best-effort catch + `logger.exception()`, router의 try/except 제거

## 4. 🟢 v1 `adpter.py` 오타
- 파일명이 `adpter.py` — `adapter.py`가 올바른 철자
- v1 수정 불가 정책이 코드 자체 수정을 의미하는지, API 동작 변경만을 의미하는지에 따라 리네임 가능 여부 결정

## 5. 🟢 v1 라우터에 response_model 없음
- v2 라우터는 `response_model=schemas.GuessResp` 등을 명시하지만 v1은 전부 없음
- v1이 프로덕션 고정이라 변경 안 하는 것이라면 괜찮지만, API 문서 품질 차이가 있음

## 6. 🟢 `give_up`이 Answer 객체를 직접 반환 — GiveUpResp와 구조 불일치
- `v2/service.py:49` — `give_up`은 `schemas.Answer` 객체를 반환
- `v2/routers.py:78` — `response_model=schemas.GiveUpResp`인데, `GiveUpResp`는 `Answer`를 상속하므로 동작은 함
- 하지만 service가 `GiveUpResp`가 아닌 `Answer`를 반환하는 건 의미적으로 불일치

## 7. 🟢 `guess` 응답을 dict로 구성 후 response_model로 검증 — 이중 변환
- `v2/service.py:26-29` — 응답을 dict로 구성하고, 라우터에서 `response_model=GuessResp`로 다시 파싱
- 처음부터 `GuessResp(correct=True, ...)` 로 생성하면 타입 안전성도 높아지고 변환 비용도 없음
- `hint` 메서드도 동일한 패턴

## 8. 🟢 `guess`에서 정답일 때 answer 조회 — 추가 Redis 호출
- `v2/service.py:24-26` — 정답이면 `_get_answer`로 Redis에 한 번 더 조회
- 정답 데이터를 scores_map에 함께 저장하거나, pipeline으로 한 번에 가져오면 RTT 절약 가능
- 현재 규모에선 큰 문제 아니지만, 최적화 여지 있음

## 9. 🟢 `configs.max_rank`를 라우터에서 직접 참조
- `v1/routers.py:32`, `v2/routers.py:55` — `Path(ge=0, le=configs.max_rank)` 에서 config을 직접 import
- 서비스/빌더에선 DI로 `max_rank`를 주입받는데, 라우터에선 직접 참조 → 기존 피드백 "config 주입 비일관" 항목과 동일 이슈

---

# Stats API 리뷰

## 1. ~~🔴 `get_stats_daily`에 인증이 없음~~ — 해당 없음
- 비로그인 상태에서도 user_id로 타인의 일별 통계를 조회할 수 있는 것은 **의도된 설계**
- 공개 프로필/통계 성격의 엔드포인트

## 2. ~~🟡 `fetch_all_results`가 date range 없이 DB 전체 조회~~ — 해당 없음
- 유저당 하루 1row이고 `WHERE user_id = ...` 조건이므로, 실제로는 유저별 최대 ~1,095 row(3년) 수준
- streak 계산에 `start_date` 이전 데이터도 필요하여 date range 필터를 넣으면 오히려 로직이 복잡해짐
- 현재 규모에서 성능 문제 없음

## 3. ~~🟡 `flush_stats`가 청크마다 개별 commit~~ — 해당 없음
- upsert로 멱등성이 보장되므로 부분 flush 후 재실행해도 데이터 정합성 유지
- 단일 트랜잭션으로 묶으면 DB 락 범위 증가, 마지막 청크 실패 시 전체 롤백으로 재실행 비용이 더 큼
- 청크별 commit + 멱등 upsert가 현재 케이스에 더 적합

## 4. ~~🟡 `get_overview`에 date range 검증이 없음~~ ✅ 해결
- **해결**: `StatService.get_overview`에서 `start_date > end_date` 시 `InvalidDateRange` 예외 발생, 라우터에서 400 반환
- 과도한 범위 제한은 기준 미정으로 보류

## 5. 🟢 `StatDailyResp.status`가 `str` 타입 — enum 미사용
- `schemas/stats.py:33` — `status: str`로 선언
- `UserQuizStatus` enum이 이미 존재하므로 이를 사용하면 API 문서에 허용 값이 명시되고, 잘못된 값 유입 방지 가능
- `QuizResultEntry.status`도 동일하게 str → enum 전환 고려

## 6. 🟢 `_process_and_upsert_chunk`에서 key 파싱이 취약
- `repository.py:169` — `user_id = key.split(":")[1]`로 Redis key에서 user_id 추출
- key 포맷 `user:{user_id}:quiz:{date}:stat`에 암묵적으로 의존
- `RedisStatKeys`에 `extract_user_id(key)` 같은 정적 메서드를 두면 `RedisQuizKeys.extract_date`와 패턴 일관성 확보

## 7. 🟢 Lua script 반환값(0/1)을 caller에서 사용하지 않음
- `redis_scripts.py` — 모든 Lua script가 이미 terminal state이면 `0`, 처리했으면 `1` 반환
- `repository.py:30-41` — `record_guess`, `record_hint`, `record_giveup` 모두 반환값을 무시
- 현재는 문제없지만, 이미 SUCCESS/GIVEUP인데 추가 기록 시도가 있었다는 정보를 로깅이나 응답에 활용할 수 있음
