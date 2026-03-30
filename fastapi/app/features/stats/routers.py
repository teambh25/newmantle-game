import datetime

from fastapi import APIRouter, Depends, HTTPException, status

import app.exceptions as exc
from app.cores.auth import get_required_user
from app.dependencies import get_stat_service
from app.features.stats.service import StatService
from app.schemas.stats import StatDailyResp, StatOverviewResp

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
    user_id: str = Depends(get_required_user),
):
    try:
        return await stat_service.get_overview(user_id, start_date, end_date)
    except exc.InvalidDateRange as e:
        raise HTTPException(status_code=400, detail=str(e))


@stats_router.get(
    "/{user_id}/{date}",
    status_code=status.HTTP_200_OK,
    response_model=StatDailyResp,
)
async def get_stats_daily(
    user_id: str,
    date: datetime.date,
    stat_service: StatService = Depends(get_stat_service),
):
    try:
        return await stat_service.get_daily(user_id, date)
    except exc.StatNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
