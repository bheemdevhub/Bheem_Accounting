# app/modules/accounting/config.py
"""Configuration settings for Accounting module"""
from enum import Enum
from typing import Dict, List


class AccountType(Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class TransactionType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class JournalEntryStatus(Enum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class InvoiceStatus(Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    REFUNDED = "refunded"


class AccountingEventTypes:
    """Event types for Accounting module"""
    
    # Account events
    ACCOUNT_CREATED = "accounting.account.created"
    ACCOUNT_UPDATED = "accounting.account.updated"
    ACCOUNT_DELETED = "accounting.account.deleted"
    
    # Journal entry events
    JOURNAL_ENTRY_CREATED = "accounting.journal_entry.created"
    JOURNAL_ENTRY_POSTED = "accounting.journal_entry.posted"
    JOURNAL_ENTRY_CANCELLED = "accounting.journal_entry.cancelled"
    
    # Invoice events
    INVOICE_CREATED = "accounting.invoice.created"
    INVOICE_SENT = "accounting.invoice.sent"
    INVOICE_PAID = "accounting.invoice.paid"
    INVOICE_OVERDUE = "accounting.invoice.overdue"
    INVOICE_CANCELLED = "accounting.invoice.cancelled"
    
    # Payment events
    PAYMENT_CREATED = "accounting.payment.created"
    PAYMENT_PROCESSED = "accounting.payment.processed"
    PAYMENT_FAILED = "accounting.payment.failed"
    PAYMENT_REFUNDED = "accounting.payment.refunded"
    
    # Report events
    FINANCIAL_REPORT_GENERATED = "accounting.report.generated"
    TAX_REPORT_GENERATED = "accounting.tax_report.generated"
    
    # Budget events
    BUDGET_CREATED = "accounting.budget.created"
    BUDGET_EXCEEDED = "accounting.budget.exceeded"
    
    # Reconciliation events
    BANK_RECONCILIATION_STARTED = "accounting.reconciliation.started"
    BANK_RECONCILIATION_COMPLETED = "accounting.reconciliation.completed"
    
    # Inventory integration events
    INVENTORY_STOCK_MOVEMENT_POSTED = "inventory.stock_movement_posted"
    INVENTORY_ADJUSTMENT_POSTED = "inventory.inventory_adjustment_posted"
    
    # Fiscal year events
    FISCAL_YEAR_CREATED = "accounting.fiscal_year.created"
    FISCAL_YEAR_UPDATED = "accounting.fiscal_year.updated"
    FISCAL_YEAR_CLOSED = "accounting.fiscal_year.closed"
    # Fiscal period events (add these for completeness)
    FISCAL_PERIOD_CREATED = "accounting.fiscal_period.created"
    FISCAL_PERIOD_UPDATED = "accounting.fiscal_period.updated"
    FISCAL_PERIOD_CLOSED = "accounting.fiscal_period.closed"
    FISCAL_PERIOD_DELETED = "accounting.fiscal_period.deleted"


class ModuleConfig:
    """Configuration constants for Accounting module"""
    
    # Default settings
    DEFAULT_CURRENCY = "USD"
    DECIMAL_PLACES = 2
    
    # Chart of accounts
    DEFAULT_ACCOUNT_CODE_LENGTH = 4
    ACCOUNT_CODE_SEPARATOR = "-"
    
    # Invoice settings
    INVOICE_NUMBER_PREFIX = "INV-"
    INVOICE_DUE_DAYS = 30
    OVERDUE_REMINDER_DAYS = [7, 14, 30]
    
    # Payment settings
    PAYMENT_REFERENCE_PREFIX = "PAY-"
    AUTO_RECONCILIATION_THRESHOLD = 0.01  # $0.01
    
    # Tax settings
    DEFAULT_TAX_RATE = 0.0825  # 8.25%
    TAX_ROUNDING_METHOD = "round_half_up"
    
    # Reporting settings
    FISCAL_YEAR_START_MONTH = 1  # January
    REPORTING_PERIODS = ["monthly", "quarterly", "annually"]
    
    # Performance settings
    MAX_TRANSACTIONS_PER_BATCH = 1000
    CACHE_TIMEOUT_SECONDS = 300


# Permission definitions
ACCOUNTING_PERMISSIONS = {
    # Account permissions
    "accounting.create_account": "Create chart of accounts",
    "accounting.update_account": "Update account information",
    "accounting.view_account": "View account details",
    "accounting.delete_account": "Delete accounts",
    
    # Journal entry permissions
    "accounting.create_journal_entry": "Create journal entries",
    "accounting.update_journal_entry": "Update journal entries",
    "accounting.view_journal_entry": "View journal entries",
    "accounting.post_journal_entry": "Post journal entries",
    "accounting.cancel_journal_entry": "Cancel journal entries",
    
    # Invoice permissions
    "accounting.create_invoice": "Create invoices",
    "accounting.update_invoice": "Update invoices",
    "accounting.view_invoice": "View invoices",
    "accounting.send_invoice": "Send invoices to customers",
    "accounting.cancel_invoice": "Cancel invoices",
    
    # Payment permissions
    "accounting.create_payment": "Create payments",
    "accounting.process_payment": "Process payments",
    "accounting.view_payment": "View payment details",
    "accounting.refund_payment": "Process refunds",
    
    # Reporting permissions
    "accounting.view_financial_reports": "View financial reports",
    "accounting.generate_reports": "Generate custom reports",
    "accounting.view_tax_reports": "View tax reports",
    "accounting.export_reports": "Export reports",
    
    # Budget permissions
    "accounting.create_budget": "Create budgets",
    "accounting.update_budget": "Update budgets",
    "accounting.view_budget": "View budget information",
    "accounting.approve_budget": "Approve budgets",
    
    # Reconciliation permissions
    "accounting.bank_reconciliation": "Perform bank reconciliation",
    "accounting.auto_reconciliation": "Use automatic reconciliation",
    
    # Admin permissions
    "accounting.admin_settings": "Manage accounting settings",
    "accounting.manage_chart_of_accounts": "Manage chart of accounts structure",
    "accounting.view_audit_trail": "View accounting audit trail"
}

# API Endpoint configurations
API_ENDPOINTS = {
    "accounts": [
        "GET /accounting/accounts/",
        "POST /accounting/accounts/",
        "GET /accounting/accounts/{id}",
        "PUT /accounting/accounts/{id}",
        "DELETE /accounting/accounts/{id}",
        "GET /accounting/accounts/{id}/transactions/",
    ],
    "journal_entries": [
        "GET /accounting/journal-entries/",
        "POST /accounting/journal-entries/",
        "GET /accounting/journal-entries/{id}",
        "PUT /accounting/journal-entries/{id}",
        "POST /accounting/journal-entries/{id}/post",
        "POST /accounting/journal-entries/{id}/cancel",
    ],
    "invoices": [
        "GET /accounting/invoices/",
        "POST /accounting/invoices/",
        "GET /accounting/invoices/{id}",
        "PUT /accounting/invoices/{id}",
        "POST /accounting/invoices/{id}/send",
        "POST /accounting/invoices/{id}/cancel",
        "GET /accounting/invoices/{id}/pdf",
    ],
    "payments": [
        "GET /accounting/payments/",
        "POST /accounting/payments/",
        "GET /accounting/payments/{id}",
        "POST /accounting/payments/{id}/process",
        "POST /accounting/payments/{id}/refund",
    ],
    "reports": [
        "GET /accounting/reports/balance-sheet/",
        "GET /accounting/reports/income-statement/",
        "GET /accounting/reports/cash-flow/",
        "GET /accounting/reports/trial-balance/",
        "GET /accounting/reports/tax-summary/",
    ],
    "reconciliation": [
        "GET /accounting/reconciliation/banks/",
        "POST /accounting/reconciliation/start",
        "POST /accounting/reconciliation/match-transactions",
        "POST /accounting/reconciliation/complete",
    ]
}

