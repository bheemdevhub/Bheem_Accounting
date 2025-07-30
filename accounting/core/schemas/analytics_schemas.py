
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field

class AnalyticsDashboardResponse(BaseModel):
    daily_activities: List['DailyActivityCount']
    top_accounts: List['AccountActivitySummary']
    cash_flow: List['CashFlowByDay']
    outstanding: List['OutstandingSummary']
    asset_changes: List['AssetChangeByDay']
    user_activity: List['UserActivitySummary']
    trends: List['TrendSummary']

# --- Analytics Response Schemas ---
class DailyActivityCount(BaseModel):
    date: str
    activity_type: str
    count: int

class AccountActivitySummary(BaseModel):
    account_id: str
    account_name: str
    activity_count: int

class CashFlowByDay(BaseModel):
    date: str
    inflow: float
    outflow: float
    net_flow: float

class OutstandingSummary(BaseModel):
    date: date
    receivables: float
    payables: float

class AssetChangeByDay(BaseModel):
    date: str
    asset_type: str
    change: float

class UserActivitySummary(BaseModel):
    user_id: str
    user_name: str
    activity_count: int

class TrendSummary(BaseModel):
    date: str
    metric: str
    value: float


# --- Analytics API Response Models ---
class DailyActivityResponse(BaseModel):
    activities: List[DailyActivityCount]

class TrendResponse(BaseModel):
    trends: List[TrendSummary]

class TopAccountsResponse(BaseModel):
    accounts: List[AccountActivitySummary]

class CashFlowResponse(BaseModel):
    cash_flow: List[CashFlowByDay]

class OutstandingResponse(BaseModel):
    outstanding: List[OutstandingSummary]

class AssetChangeResponse(BaseModel):
    asset_changes: List[AssetChangeByDay]

class UserActivityResponse(BaseModel):
    user_activity: List[UserActivitySummary]


