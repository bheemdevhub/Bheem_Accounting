from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional
from datetime import date
from uuid import UUID
from bheem_core.modules.accounting.core.services.analytics_service import AccountingAnalyticsService
from bheem_core.modules.accounting.core.schemas.analytics_schemas import (
    DailyActivityResponse, TrendResponse, TopAccountsResponse, CashFlowResponse, OutstandingResponse, AssetChangeResponse, UserActivityResponse
)
from bheem_core.modules.auth.core.services.permissions_service import require_roles, require_api_permission
from bheem_core.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/analytics", tags=["Accounting Analytics"])

@router.get("/daily-activity", response_model=DailyActivityResponse, summary="Get daily accounting activities",
    dependencies=[Depends(lambda: require_api_permission("accounting.analytics.read")), Depends(lambda: require_roles(["ACCOUNTANT", "ADMIN"]))])
async def get_daily_activity(
    date_: Optional[date] = Query(None, description="Date for activity (default today)"),
    db: AsyncSession = Depends(get_db)
):
    service = AccountingAnalyticsService(db)
    return await service.get_daily_activity(date_)

@router.get("/trends", response_model=TrendResponse, summary="Get accounting trends",
    dependencies=[Depends(lambda: require_api_permission("accounting.analytics.read")), Depends(lambda: require_roles(["ACCOUNTANT", "ADMIN"]))])
async def get_trends(
    days: int = Query(30, ge=1, le=90, description="Number of days for trend analysis"),
    db: AsyncSession = Depends(get_db)
):
    service = AccountingAnalyticsService(db)
    return await service.get_trends(days)

@router.get("/top-accounts", response_model=TopAccountsResponse, summary="Get top accounts by activity",
    dependencies=[Depends(lambda: require_api_permission("accounting.analytics.read")), Depends(lambda: require_roles(["ACCOUNTANT", "ADMIN"]))])
async def get_top_accounts(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    service = AccountingAnalyticsService(db)
    return await service.get_top_accounts(limit)

@router.get("/cash-flow", response_model=CashFlowResponse, summary="Get cash flow by day",
    dependencies=[Depends(lambda: require_api_permission("accounting.analytics.read")), Depends(lambda: require_roles(["ACCOUNTANT", "ADMIN"]))])
async def get_cash_flow(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db)
):
    service = AccountingAnalyticsService(db)
    return await service.get_cash_flow(start_date, end_date)

@router.get("/outstanding", response_model=OutstandingResponse, summary="Get outstanding receivables/payables",
    dependencies=[Depends(lambda: require_api_permission("accounting.analytics.read")), Depends(lambda: require_roles(["ACCOUNTANT", "ADMIN"]))])
async def get_outstanding(
    db: AsyncSession = Depends(get_db)
):
    service = AccountingAnalyticsService(db)
    return await service.get_outstanding()

@router.get("/asset-changes", response_model=AssetChangeResponse, summary="Get asset changes by day",
    dependencies=[Depends(lambda: require_api_permission("accounting.analytics.read")), Depends(lambda: require_roles(["ACCOUNTANT", "ADMIN"]))])
async def get_asset_changes(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db)
):
    service = AccountingAnalyticsService(db)
    return await service.get_asset_changes(start_date, end_date)

@router.get("/user-activity", response_model=UserActivityResponse, summary="Get user/team activity",
    dependencies=[Depends(lambda: require_api_permission("accounting.analytics.read")), Depends(lambda: require_roles(["ACCOUNTANT", "ADMIN"]))])
async def get_user_activity(
    date_: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    service = AccountingAnalyticsService(db)
    return await service.get_user_activity(date_)

