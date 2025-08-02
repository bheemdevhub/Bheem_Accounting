# app/modules/accounting/module.py
"""Main Accounting Module Class"""
from typing import List
from ...core.base_module import BaseERPModule
from .api.v1.routes import accounts, journal_entries, invoices, reports, budget, companies, cost_centers, profit_centers, currencies, fiscal_years
from app.modules.auth.core.services.permissions_service import require_roles, require_api_permission
from .config import AccountingEventTypes, ACCOUNTING_PERMISSIONS
from .events.handlers import AccountingEventHandlers
import logging


class AccountingModule(BaseERPModule):
    """Accounting and Financial Management Module"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_handlers = None
    
    @property
    def name(self) -> str:
        return "accounting"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def permissions(self) -> List[str]:
        return list(ACCOUNTING_PERMISSIONS.keys())

    def _setup_routes(self) -> None:
        """Setup Accounting module routes"""
        from .api.v1.routes import analytics
        self._router.include_router(accounts.router, prefix="/accounts", tags=["Accounts"])
        self._router.include_router(analytics.router, prefix="/analytics", tags=["Accounting Analytics"])
        self._router.include_router(journal_entries.router, prefix="/journal-entries", tags=["Journal Entries"])
        self._router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
        self._router.include_router(reports.router, prefix="/reports", tags=["Reports"])
        self._router.include_router(budget.router, prefix="/budgets", tags=["Budgets"])
        self._router.include_router(companies.router, prefix="/companies", tags=["Companies"])
        self._router.include_router(cost_centers.router, prefix="/cost-centers", tags=["Cost Centers"])
        self._router.include_router(profit_centers.router, prefix="/profit-centers", tags=["Profit Centers"])
        self._router.include_router(currencies.router, prefix="/currencies", tags=["Currencies"])
        self._router.include_router(fiscal_years.router, prefix="/fiscal-years", tags=["Fiscal Years"])
        # Add module health endpoint (inherited from base)
        super()._setup_routes()

    async def _subscribe_to_events(self) -> None:
        """Subscribe to events from other modules"""
        if self._event_bus:
            # Initialize event handlers
            # Note: service would be injected in a real implementation
            self._event_handlers = AccountingEventHandlers(service=None)
            
            # Listen for system events
            await self._event_bus.subscribe("system.company_created", self._event_handlers.handle_company_created)
            
            # Listen for internal accounting events
            await self._event_bus.subscribe(AccountingEventTypes.JOURNAL_ENTRY_POSTED, self._event_handlers.handle_journal_entry_posted)
            await self._event_bus.subscribe(AccountingEventTypes.INVOICE_CREATED, self._event_handlers.handle_invoice_created)
            await self._event_bus.subscribe(AccountingEventTypes.INVOICE_PAID, self._event_handlers.handle_invoice_paid)
            await self._event_bus.subscribe(AccountingEventTypes.PAYMENT_PROCESSED, self._event_handlers.handle_payment_processed)
            await self._event_bus.subscribe(AccountingEventTypes.BUDGET_EXCEEDED, self._event_handlers.handle_budget_exceeded)
            await self._event_bus.subscribe(AccountingEventTypes.INVOICE_OVERDUE, self._event_handlers.handle_invoice_overdue)
            await self._event_bus.subscribe(AccountingEventTypes.BANK_RECONCILIATION_COMPLETED, self._event_handlers.handle_bank_reconciliation_completed)
            await self._event_bus.subscribe(AccountingEventTypes.FINANCIAL_REPORT_GENERATED, self._event_handlers.handle_financial_report_generated)
            
            # Listen for inter-module events
            await self._event_bus.subscribe("sales.order_created", self._event_handlers.handle_sales_order_created)
            await self._event_bus.subscribe(AccountingEventTypes.INVENTORY_STOCK_MOVEMENT_POSTED, self._event_handlers.handle_inventory_stock_movement_posted)
            await self._event_bus.subscribe(AccountingEventTypes.INVENTORY_ADJUSTMENT_POSTED, self._event_handlers.handle_inventory_adjustment_posted)

    async def initialize(self) -> None:
        """Initialize Accounting module"""
        await super().initialize()
        await self._subscribe_to_events()
        self._logger.info("Accounting Module initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Accounting module"""
        self._logger.info("Shutting down Accounting Module")
        # Cleanup resources, close connections, etc.
        await super().shutdown()
