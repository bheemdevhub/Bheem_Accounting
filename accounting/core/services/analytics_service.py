

from sqlalchemy.ext.asyncio import AsyncSession

from bheem_core.modules.accounting.core.schemas.analytics_schemas import (
    DailyActivityCount, AccountActivitySummary, CashFlowByDay, OutstandingSummary, AssetChangeByDay, UserActivitySummary, TrendSummary, AnalyticsDashboardResponse
)
from datetime import date

class AccountingAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_daily_activities(self, start_date: date, end_date: date) -> list[DailyActivityCount]:
        stmt = select(
            func.date(JournalEntry.created_at).label('date'),
            JournalEntry.entry_type,
            func.count().label('count')
        ).where(
            JournalEntry.created_at >= start_date,
            JournalEntry.created_at <= end_date
        ).group_by(func.date(JournalEntry.created_at), JournalEntry.entry_type)
        result = await self.db.execute(stmt)
        return [DailyActivityCount(date=row.date, activity_type=row.entry_type, count=row.count) for row in result]

    async def get_top_accounts(self, start_date: date, end_date: date, limit: int = 5) -> list[AccountActivitySummary]:
        stmt = select(
            Account.id, Account.account_name, func.count(JournalEntry.id).label('activity_count')
        ).join(JournalEntry, JournalEntry.account_id == Account.id)
        stmt = stmt.where(JournalEntry.created_at >= start_date, JournalEntry.created_at <= end_date)
        stmt = stmt.group_by(Account.id, Account.account_name).order_by(func.count(JournalEntry.id).desc()).limit(limit)
        result = await self.db.execute(stmt)
        return [AccountActivitySummary(account_id=str(row.id), account_name=row.account_name, activity_count=row.activity_count) for row in result]

    async def get_cash_flow_by_day(self, start_date: date, end_date: date) -> list[CashFlowByDay]:
        stmt = select(
            func.date(Payment.payment_date).label('date'),
            func.sum(Payment.amount).filter(Payment.amount > 0).label('inflow'),
            func.sum(Payment.amount).filter(Payment.amount < 0).label('outflow')
        ).where(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).group_by(func.date(Payment.payment_date)).order_by('date')
        result = await self.db.execute(stmt)
        return [CashFlowByDay(date=row.date, inflow=row.inflow or 0, outflow=abs(row.outflow or 0), net_flow=(row.inflow or 0)-(abs(row.outflow or 0))) for row in result]

    async def get_outstanding_summary(self, as_of: date) -> OutstandingSummary:
        stmt_receivables = select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0)).where(
            and_(Invoice.type == "SALES_INVOICE", Invoice.status != "FULLY_PAID", Invoice.created_at <= as_of)
        )
        stmt_payables = select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0)).where(
            and_(Invoice.type == "PURCHASE_INVOICE", Invoice.status != "FULLY_PAID", Invoice.created_at <= as_of)
        )
        receivables = float((await self.db.execute(stmt_receivables)).scalar() or 0)
        payables = float((await self.db.execute(stmt_payables)).scalar() or 0)
        return OutstandingSummary(date=as_of, receivables=receivables, payables=payables)

    async def get_asset_changes(self, start_date: date, end_date: date) -> list[AssetChangeByDay]:
        stmt = select(
            func.date(FixedAsset.acquisition_date).label('date'),
            FixedAsset.asset_type,
            func.sum(FixedAsset.value).label('change')
        ).where(
            FixedAsset.acquisition_date >= start_date,
            FixedAsset.acquisition_date <= end_date
        ).group_by(func.date(FixedAsset.acquisition_date), FixedAsset.asset_type)
        result = await self.db.execute(stmt)
        return [AssetChangeByDay(date=row.date, asset_type=row.asset_type, change=row.change) for row in result]

    async def get_user_activity(self, start_date: date, end_date: date) -> list[UserActivitySummary]:
        stmt = select(
            JournalEntry.created_by, func.count(JournalEntry.id).label('activity_count')
        ).where(
            JournalEntry.created_at >= start_date,
            JournalEntry.created_at <= end_date
        ).group_by(JournalEntry.created_by)
        result = await self.db.execute(stmt)
        return [UserActivitySummary(user_id=str(row.created_by), user_name=str(row.created_by), activity_count=row.activity_count) for row in result]

    async def get_trends(self, metric: str, start_date: date, end_date: date) -> list[TrendSummary]:
        # Example: metric could be 'revenue', 'expenses', etc.
        stmt = select(
            func.date(Invoice.created_at).label('date'),
            func.sum(Invoice.total_amount).label('value')
        ).where(
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).group_by(func.date(Invoice.created_at)).order_by('date')
        result = await self.db.execute(stmt)
        return [TrendSummary(date=row.date, metric=metric, value=row.value) for row in result]

    async def get_dashboard(self, start_date: date, end_date: date) -> AnalyticsDashboardResponse:
        daily_activities = await self.get_daily_activities(start_date, end_date)
        top_accounts = await self.get_top_accounts(start_date, end_date)
        cash_flow = await self.get_cash_flow_by_day(start_date, end_date)
        outstanding = [await self.get_outstanding_summary(end_date)]
        asset_changes = await self.get_asset_changes(start_date, end_date)
        user_activity = await self.get_user_activity(start_date, end_date)
        trends = await self.get_trends('revenue', start_date, end_date)
        return AnalyticsDashboardResponse(
            daily_activities=daily_activities,
            top_accounts=top_accounts,
            cash_flow=cash_flow,
            outstanding=outstanding,
            asset_changes=asset_changes,
            user_activity=user_activity,
            trends=trends
        )

