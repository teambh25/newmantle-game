# Stats API

Base URL: `/v2/stats`

인증 방식은 엔드포인트별로 다릅니다. 각 섹션의 요청 예시를 참고하세요.

---

## 1. GET `/v2/stats` - 통계 Overview (캘린더 + 요약)

회원의 지정한 날짜 범위의 캘린더 항목과 요약 통계를 반환합니다. (게스트는 사용 불가)

### 요청

| 파라미터     | 타입   | 위치  | 필수 | 설명                                  |
|-------------|--------|-------|------|---------------------------------------|
| `start_date` | `date` | query | O    | 조회 시작일 (ISO 8601, 예: `2026-03-01`) |
| `end_date`   | `date` | query | O    | 조회 종료일 (ISO 8601, 예: `2026-03-16`) |

```
GET /v2/stats?start_date=2026-03-01&end_date=2026-03-16
Authorization: Bearer <token>
```

### 응답 `200 OK`

```json
{
  "calendar": [
    {
      "date": "2026-03-01",
      "status": "SUCCESS_WITHOUT_HINT"
    },
    {
      "date": "2026-03-02",
      "status": "SUCCESS_WITH_HINT"
    },
    {
      "date": "2026-03-03",
      "status": "FAIL"
    },
    {
      "date": "2026-03-05",
      "status": "OUTAGE"
    }
  ],
  "summary": {
    "total_success_days": 10,
    "current_streak": 3,
    "max_streak": 7,
    "avg_guess_when_correct": 42.5,
    "avg_hints_when_correct": 1.2
  }
}
```

### 응답 스키마

**`StatOverviewResp`**

| 필드       | 타입              | 설명                                  |
|-----------|-------------------|---------------------------------------|
| `calendar` | `CalendarEntry[]` | 날짜별 항목 (날짜 오름차순 정렬)          |
| `summary`  | `StatSummary`     | 전체 기간 요약 통계                      |

**`CalendarEntry`**

| 필드     | 타입     | 설명          |
|---------|----------|---------------|
| `date`   | `date`   | 퀴즈 날짜      |
| `status` | `string` | 아래 캘린더 상태 값 중 하나 |

**`CalendarStatus` 값**

| 값                       | 설명                          |
|-------------------------|-------------------------------|
| `SUCCESS_WITHOUT_HINT`   | 힌트 없이 정답을 맞춤            |
| `SUCCESS_WITH_HINT`      | 힌트를 사용하여 정답을 맞춤       |
| `FAIL`                   | 포기했거나 실패                  |
| `OUTAGE`                 | 서버 장애일 (퀴즈 없음)          |

**`StatSummary`**

| 필드                     | 타입    | 설명                              |
|-------------------------|---------|-----------------------------------|
| `total_success_days`     | `int`   | 총 정답 일수                       |
| `current_streak`         | `int`   | 현재 연속 정답 일수                  |
| `max_streak`             | `int`   | 최대 연속 정답 일수                  |
| `avg_guess_when_correct` | `float` | 정답 시 평균 추측 횟수               |
| `avg_hints_when_correct` | `float` | 정답 시 평균 힌트 사용 횟수           |

> **참고**: 플레이 기록이 없고 장애일도 아닌 날짜는 캘린더 배열에서 **생략**됩니다.

### 에러

| 상태 코드 | 발생 조건                                    | 응답 예시                                |
|----------|---------------------------------------------|------------------------------------------|
| `400`    | `start_date`가 `end_date`보다 이후일 때         | `{"detail": "InvalidDateRange: start_date must not be after end_date"}` |
| `401`    | `Authorization` 헤더가 없거나 토큰이 유효하지 않을 때 | `{"detail": "Authentication failed"}`    |
| `422`    | `start_date` 또는 `end_date`가 누락되었거나 형식이 잘못되었을 때 | FastAPI 기본 validation error 형식 |

---

## 2. GET `/v2/stats/{user_type}/{subject_id}/{date}` - 일별 상세 통계

특정 유저(회원 또는 게스트)의 특정 날짜 상세 통계를 반환합니다. 인증 불필요 (공개 조회).

### 요청

| 파라미터       | 타입     | 위치 | 필수 | 설명                                     |
|---------------|----------|------|------|------------------------------------------|
| `user_type`    | `string` | path | O    | `user` 또는 `guest`                       |
| `subject_id`   | `uuid`   | path | O    | 조회할 유저/게스트 ID (UUID 형식)            |
| `date`         | `date`   | path | O    | 퀴즈 날짜 (ISO 8601, 예: `2026-03-16`)     |

```
GET /v2/stats/user/550e8400-e29b-41d4-a716-446655440000/2026-03-16
GET /v2/stats/guest/a1b2c3d4-e5f6-7890-abcd-ef1234567890/2026-03-16
```

### 응답 `200 OK`

```json
{
  "date": "2026-03-16",
  "status": "SUCCESS",
  "guess_count": 35,
  "hint_count": 2
}
```

### 응답 스키마

**`StatDailyResp`**

| 필드          | 타입     | 설명                                        |
|--------------|----------|---------------------------------------------|
| `date`        | `date`   | 퀴즈 날짜                                    |
| `status`      | `string` | `"SUCCESS"`, `"FAIL"`, `"GIVEUP"` 중 하나 |
| `guess_count` | `int`    | 총 추측 횟수                                  |
| `hint_count`  | `int`    | 총 힌트 사용 횟수                              |

### 에러

| 상태 코드 | 발생 조건                                    | 응답 예시                                          |
|----------|---------------------------------------------|----------------------------------------------------|
| `404`    | 해당 날짜에 대한 통계 기록이 없을 때                | `{"detail": "No stat found for 2026-03-16"}`       |
| `422`    | `user_type`이 `user`/`guest`가 아니거나, `subject_id`가 UUID 형식이 아니거나, `date` 형식이 잘못되었을 때 | FastAPI 기본 validation error 형식                  |

---

## 3. POST `/v2/stats/link` - 게스트 스탯 연동

게스트 스탯을 회원 계정에 연동합니다. 로그인 후 1회 호출합니다. JWT 필수.

### 요청

| 파라미터     | 타입   | 위치 | 필수 | 설명                        |
|-------------|--------|------|------|-----------------------------|
| `guest_id`   | `uuid` | body | O    | 연동할 게스트 ID (UUID 형식)   |

```
POST /v2/stats/link
Authorization: Bearer <token>
Content-Type: application/json

{
  "guest_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 응답 `204 No Content`

본문 없음.

### 에러

| 상태 코드 | 발생 조건                                    | 응답 예시                                |
|----------|---------------------------------------------|------------------------------------------|
| `401`    | `Authorization` 헤더가 없거나 토큰이 유효하지 않을 때 | `{"detail": "Authentication failed"}`    |
| `422`    | `guest_id`가 누락되었거나 UUID 형식이 아닐 때       | FastAPI 기본 validation error 형식        |
