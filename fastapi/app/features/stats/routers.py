import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

import app.exceptions as exc
from app.cores.auth import get_current_user
from app.dependencies import get_stat_service
from app.features.stats.service import StatService
from app.schemas.stats import (
    StatDailyResp,
    StatLinkReq,
    StatOverviewResp,
    UserType,
)

stats_router = APIRouter(prefix="/v2/stats", tags=["Stats"])


@stats_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=StatOverviewResp,
)
async def get_stats_overview(
    start_date: datetime.date,
    end_date: datetime.date,
    stat_service: StatService = Depends(get_stat_service),
    user_id: str = Depends(get_current_user),
):
    try:
        calendar, summary = await stat_service.get_overview(
            user_id, start_date, end_date
        )
        return StatOverviewResp(calendar=calendar, summary=summary)
    except exc.InvalidDateRange as e:
        raise HTTPException(status_code=400, detail=str(e))


@stats_router.get(
    "/{user_type}/{subject_id}/{date}",
    status_code=status.HTTP_200_OK,
    response_model=StatDailyResp,
)
async def get_stats_daily(
    user_type: UserType,
    subject_id: uuid.UUID,
    date: datetime.date,
    stat_service: StatService = Depends(get_stat_service),
):
    try:
        stat = await stat_service.get_daily(subject_id, user_type, date)
        return StatDailyResp(
            date=date,
            status=stat.status,
            guess_count=stat.guess_count,
            hint_count=stat.hint_count,
        )
    except exc.StatNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@stats_router.post(
    "/link",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def link_guest_stats(
    req: StatLinkReq,
    stat_service: StatService = Depends(get_stat_service),
    user_id: str = Depends(get_current_user),
):
    await stat_service.link_guest_stats(user_id, req.guest_id)
