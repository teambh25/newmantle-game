# Outage Date Admin API Design

## 개요

서버 장애로 게임이 불가능했던 날짜를 관리하는 Admin API.
등록된 날짜는 Stats 조회 시 `OUTAGE` 상태로 최우선 판정되어, 해당 날짜의 FAIL/SUCCESS 기록을 덮어씀.

## API

### 1. 장애일 목록 조회

```
GET /admin/outage-dates
```

- Auth: Admin Basic Auth
- 전체 장애일 목록 반환 (날짜 오름차순)

```json
{
  "outage_dates": ["2026-01-15", "2026-02-20"]
}
```

### 2. 장애일 등록

```
POST /admin/outage-dates
```

- Auth: Admin Basic Auth
- 이미 존재하면 무시 (`ON CONFLICT DO NOTHING`), 201 반환

```json
// Request
{ "date": "2026-01-15" }

// Response (201)
{ "date": "2026-01-15" }
```

### 3. 장애일 삭제

```
DELETE /admin/outage-dates/{date}
```

- Auth: Admin Basic Auth
- 존재하지 않으면 404

```json
// Response (200)
{ "date": "2026-01-15" }
```

## 설계 결정

- **캐싱 없음**: outage_dates는 10건 미만이므로 DB 직접 조회로 충분
- **멱등성**: POST는 `ON CONFLICT DO NOTHING`으로 중복 등록 안전
- **기존 Admin router에 추가**: `admin_router`에 기존 패턴(`Depends(authenticate_admin)`)과 동일하게 추가
- **별도 router vs 기존 router**: 기존 `admin_router`에 엔드포인트 추가 (Admin 도메인이 동일하므로 분리 불필요)
- **Repository 위치**: `features/common/outage_repository.py`에 `OutageDateRepository`로 분리. OutageDate는 시스템 레벨 관리 데이터로 Stats(조회)와 Admin(CRUD) 양쪽에서 사용하므로 common에 배치

## 구현 범위

| 레이어 | 변경 내용 |
|--------|-----------|
| Repository | `features/common/outage_repository.py` 생성 — `StatRepository`에서 outage 관련 메서드 3개 이동 |
| Service | Admin용 thin wrapper 메서드 추가 |
| Router | `admin/routers.py`에 3개 엔드포인트 추가 |
| Schema | `OutageDateRequest` (date 필드), `OutageDateListResp` |
| Dependency | `OutageDateRepository` dependency 추가, Admin/Stats 양쪽에서 주입 |
