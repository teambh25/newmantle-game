# 내가 찾은 것
- [x] Admin Router에서 stat service를 써야되서 대대적인 코드 구조 개편이 필요할듯?
      => 지금 규모에선 유지하자..
- [x] GameRepo, Admin Repo로 분리하기엔 어색하다? => 괜찮다, 굳이 고민하자면 outageDataService정도 인데 지금처러 간단히 유지하는 것도 괜찮음

- [ ] base model이 app/features/stats/models.py에 있음
- [ ] 어디는 config를 주입하고, 어디는 config을 그대로 써서 통일 필요해보임
- [ ] graceful shutdown이 없어도 되나?

---

# Admin API 리뷰

## 1. Router에서 직접 try/except + HTTPException 변환 — exception handler 미활용
- `admin/routers.py`의 모든 엔드포인트가 `BaseAppException`을 직접 catch해서 `HTTPException`으로 변환하고 있음
- 이미 `exceptions/handlers.py`에 global exception handler 패턴이 있으므로, admin 전용 exception handler를 등록하면 라우터 코드가 훨씬 깔끔해짐
- game 라우터도 동일한 패턴이라 프로젝트 전체적으로 개선 가능
- 예: `BaseAppException` 하위 클래스에 `status_code` 속성을 두고, 하나의 handler로 통합

## 2. Validator.today가 생성 시점에 고정됨
- `Validator(today, max_rank)`에서 `today`가 DI 시점의 값으로 고정
- 현재는 요청마다 DI가 새로 생성되므로 문제 없지만, 만약 서비스가 싱글턴으로 바뀌면 날짜가 고정되는 버그 발생 가능
- 의도를 명확히 하려면 `validate_quiz(quiz, today)` 처럼 메서드 파라미터로 받는 게 더 안전

## 3. `fetch_all_answers`에서 `KEYS *answers` 사용
- `repository.py:20` — `self.rd.keys("*answers")`는 Redis `KEYS` 명령 사용
- 데이터가 적은 지금은 괜찮지만, `KEYS`는 O(N)으로 Redis를 블로킹함
- 규모가 커지면 `SCAN` 기반으로 교체 필요

## 4. `fetch_all_answers` 반환값이 tuple (answer_keys, answers)
- repo가 두 개의 리스트를 tuple로 반환 → service에서 `zip`으로 조합
- 데이터 구조가 repo와 service 사이에 암묵적으로 결합됨
- `list[dict]`나 DTO로 반환하면 더 명확

## 5. `read_all_answers` 응답에 response_model이 없음
- `routers.py:33` — `read_all_answers`는 `response_model` 없이 dict를 직접 반환
- 다른 엔드포인트(`get_outage_dates`)는 `response_model`을 명시하고 있어 비일관적
- API 문서 자동생성과 응답 검증을 위해 response_model 추가 권장

## 6. `upsert_quiz` 성공 시 응답 형태 비일관
- `upsert_quiz` → `{date: answer}`, `create_outage_date` → `{"date": date}`, `delete_answer` → `None`
- 성공 응답 형태를 통일하면 클라이언트 측 처리가 간결해짐

## 7. `delete_quiz`의 검증 로직이 분산됨
- 삭제 후에 `validate_deleted_cnt`로 결과를 검증하는 방식 → 부분 삭제 시 이미 데이터가 일부 날아간 상태
- Redis pipeline + transaction으로 삭제하면 원자적으로 처리 가능 (upsert에선 이미 pipeline 사용 중)

## 8. `extract_date`가 bytes를 처리하지 않음
- `RedisQuizKeys.extract_date(key)` — Redis에서 반환된 key가 `bytes`일 수 있음 (`decode_responses=False`인 경우)
- 현재 Redis 클라이언트 설정에 따라 다르지만, 방어 코드가 없음

---

# Game API 리뷰

## 1. v1과 v2 서비스 간 역직렬화 로직 중복
- `v1/service.py:55-62` — `_extract_score_and_rank`, `_extract_word_and_score`를 static method로 직접 구현
- `v2/service.py:28,41` — 동일한 역할을 `RedisQuizData.deserialize_*`로 호출
- v1은 수정 불가(프로덕션)이므로 당장 고칠 순 없지만, 같은 로직이 두 곳에 존재한다는 점 인지 필요

## 2. v2 라우터가 stat_service를 직접 호출 — 관심사 혼재
- `v2/routers.py` — guess, hint, give_up 모두 `stat_service`를 DI 받아 라우터 레벨에서 직접 호출
- 라우터가 game 로직 + stat 기록이라는 두 가지 관심사를 동시에 처리
- stat 기록을 GameServiceV2 내부로 옮기거나, 이벤트/미들웨어 패턴으로 분리하면 라우터가 깔끔해짐

## 3. stat 기록 실패 시 bare `except Exception` — 에러가 묻힘
- `v2/routers.py:42-43,69-70,98-99` — `except Exception`으로 모든 예외를 삼키고 warning만 남김
- DB 연결 에러, 스키마 변경 등 치명적 문제도 조용히 넘어갈 수 있음
- 최소한 `logger.exception()`으로 traceback을 남기거나, 특정 예외만 catch하는 게 안전

## 4. v1 `adpter.py` 오타
- 파일명이 `adpter.py` — `adapter.py`가 올바른 철자
- v1 수정 불가 정책이 코드 자체 수정을 의미하는지, API 동작 변경만을 의미하는지에 따라 리네임 가능 여부 결정

## 5. v1 라우터에 response_model 없음
- v2 라우터는 `response_model=schemas.GuessResp` 등을 명시하지만 v1은 전부 없음
- v1이 프로덕션 고정이라 변경 안 하는 것이라면 괜찮지만, API 문서 품질 차이가 있음

## 6. `give_up`이 Answer 객체를 직접 반환 — GiveUpResp와 구조 불일치
- `v2/service.py:49` — `give_up`은 `schemas.Answer` 객체를 반환
- `v2/routers.py:78` — `response_model=schemas.GiveUpResp`인데, `GiveUpResp`는 `Answer`를 상속하므로 동작은 함
- 하지만 service가 `GiveUpResp`가 아닌 `Answer`를 반환하는 건 의미적으로 불일치

## 7. `guess` 응답을 dict로 구성 후 response_model로 검증 — 이중 변환
- `v2/service.py:26-29` — 응답을 dict로 구성하고, 라우터에서 `response_model=GuessResp`로 다시 파싱
- 처음부터 `GuessResp(correct=True, ...)` 로 생성하면 타입 안전성도 높아지고 변환 비용도 없음
- `hint` 메서드도 동일한 패턴

## 8. `guess`에서 정답일 때 answer 조회 — 추가 Redis 호출
- `v2/service.py:24-26` — 정답이면 `_get_answer`로 Redis에 한 번 더 조회
- 정답 데이터를 scores_map에 함께 저장하거나, pipeline으로 한 번에 가져오면 RTT 절약 가능
- 현재 규모에선 큰 문제 아니지만, 최적화 여지 있음

## 9. `configs.max_rank`를 라우터에서 직접 참조
- `v1/routers.py:32`, `v2/routers.py:55` — `Path(ge=0, le=configs.max_rank)` 에서 config을 직접 import
- 서비스/빌더에선 DI로 `max_rank`를 주입받는데, 라우터에선 직접 참조 → 기존 피드백 "config 주입 비일관" 항목과 동일 이슈
