# app/modules/accounting/api/routes.py
"""Main router for accounting module API"""
from fastapi import APIRouter
from .v1.routes.main_routes import fiscal_router, fiscal_period_router, company_router, currency_router
from .v1.routes import (
    accounts,
    analytics, 
    budget,
    invoices,
    journal_entries,
    reports,
    cost_centers,
    profit_centers
)

# Create main router for accounting module
router = APIRouter()

# Include all route modules
router.include_router(fiscal_router)
router.include_router(fiscal_period_router) 
router.include_router(company_router)
router.include_router(currency_router)

# Include other v1 routes
router.include_router(accounts.router, prefix="/accounts", tags=["Accounts"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(budget.router, prefix="/budgets", tags=["Budgets"])
router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
router.include_router(journal_entries.router, prefix="/journal-entries", tags=["Journal Entries"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
router.include_router(cost_centers.router, prefix="/cost-centers", tags=["Cost Centers"])
router.include_router(profit_centers.router, prefix="/profit-centers", tags=["Profit Centers"])
