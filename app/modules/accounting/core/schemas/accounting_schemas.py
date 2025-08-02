from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from enum import Enum
from bheem_core.shared.models import ProfitCenterType, BudgetType, AllocationMethod, VarianceType, SignificanceLevel
from app.modules.accounting.config import JournalEntryStatus

# --- Enums ---
class AccountCategory(str, Enum):
    ASSETS = "ASSETS"
    LIABILITIES = "LIABILITIES"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSES = "EXPENSES"

class AccountType(str, Enum):
    CURRENT_ASSETS = "CURRENT_ASSETS"
    FIXED_ASSETS = "FIXED_ASSETS"
    CURRENT_LIABILITIES = "CURRENT_LIABILITIES"
    LONG_TERM_LIABILITIES = "LONG_TERM_LIABILITIES"
    SHAREHOLDERS_EQUITY = "SHAREHOLDERS_EQUITY"
    OPERATING_REVENUE = "OPERATING_REVENUE"
    OTHER_REVENUE = "OTHER_REVENUE"

class CenterType(str, Enum):
    PROFIT = "PROFIT"
    COST = "COST"
    DEPARTMENT = "DEPARTMENT"
    PROJECT = "PROJECT"

# --- Company Schemas ---
class CompanyBase(BaseModel):
    company_code: str
    company_name: str
    company_type: Optional[str] = None
    is_active: Optional[bool] = True
    legal_name: Optional[str] = None
    parent_company_id: Optional[UUID] = None
    functional_currency_id: Optional[UUID] = None
    reporting_currency_id: Optional[UUID] = None
    consolidation_method: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    is_active: Optional[bool] = None

class CompanyResponse(CompanyBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CompanyListResponse(BaseModel):
    companies: List[CompanyResponse]

# --- Profit Center Schemas ---
class ProfitCenterBase(BaseModel):
    company_id: UUID
    profit_center_code: str
    profit_center_name: str
    name: str
    center_type: ProfitCenterType  # Use ProfitCenterType, not CenterType
    parent_profit_center_id: Optional[UUID] = None
    is_active: Optional[bool] = True

class ProfitCenterCreate(ProfitCenterBase):
    pass

class ProfitCenterUpdate(BaseModel):
    profit_center_code: Optional[str] = None
    profit_center_name: Optional[str] = None
    name: Optional[str] = None
    parent_profit_center_id: Optional[UUID] = None
    is_active: Optional[bool] = None

class ProfitCenterResponse(ProfitCenterBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ProfitCenterListResponse(BaseModel):
    profit_centers: List[ProfitCenterResponse]

# --- Cost Center Schemas ---
class CostCenterBase(BaseModel):
    company_id: UUID
    cost_center_code: str
    cost_center_name: str
    name: str
    center_type: CenterType
    parent_cost_center_id: Optional[UUID] = None
    profit_center_id: Optional[UUID] = None
    is_active: Optional[bool] = True

class CostCenterCreate(CostCenterBase):
    pass

class CostCenterUpdate(BaseModel):
    name: Optional[str] = None
    parent_cost_center_id: Optional[UUID] = None
    is_active: Optional[bool] = None

class CostCenterResponse(CostCenterBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CostCenterListResponse(BaseModel):
    cost_centers: List[CostCenterResponse]

# --- Ledger Account Schemas ---
class AccountBase(BaseModel):
    company_id: UUID
    account_code: str
    account_name: str
    account_category: AccountCategory
    account_type: AccountType
    parent_account_id: Optional[UUID] = None
    is_active: Optional[bool] = True
    is_control_account: Optional[bool] = False
    is_inter_company: Optional[bool] = False
    cost_center_required: Optional[bool] = False
    sku_tracking_enabled: Optional[bool] = False
    consolidation_account_id: Optional[UUID] = None
    elimination_account: Optional[bool] = False

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    account_category: Optional[AccountCategory] = None
    account_type: Optional[AccountType] = None
    parent_account_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    is_control_account: Optional[bool] = None
    is_inter_company: Optional[bool] = None
    cost_center_required: Optional[bool] = None
    sku_tracking_enabled: Optional[bool] = None
    consolidation_account_id: Optional[UUID] = None
    elimination_account: Optional[bool] = None

class AccountResponse(AccountBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AccountListResponse(BaseModel):
    accounts: List[AccountResponse]

# --- Journal Entry Schemas ---
class JournalEntryLineBase(BaseModel):
    account_id: UUID
    description: Optional[str] = None
    cost_center_id: Optional[UUID] = None
    profit_center_id: Optional[UUID] = None

class JournalEntryLineCreate(JournalEntryLineBase):
    amount: Decimal  # Only present in create (input) schema

class JournalEntryLineResponse(JournalEntryLineBase):
    id: UUID
    journal_entry_id: UUID

    @computed_field
    @property
    def amount(self) -> Decimal:
        # Compute amount from debit_amount and credit_amount
        debit = getattr(self, 'debit_amount', None)
        credit = getattr(self, 'credit_amount', None)
        if debit is not None and debit != 0:
            return debit
        elif credit is not None and credit != 0:
            return -credit
        return Decimal(0)

    model_config = ConfigDict(from_attributes=True)

class JournalEntryBase(BaseModel):
    company_id: UUID
    entry_number: Optional[str] = None  # <-- Allow auto-generation
    entry_date: date = Field(..., alias="date")  # Accepts both 'entry_date' and 'date' in input
    reference_number: Optional[str] = Field(None, alias="reference")  # Accepts both 'reference_number' and 'reference'
    description: Optional[str] = None
    fiscal_period_id: Optional[UUID] = None
    lines: Optional[List["JournalEntryLineCreate"]] = None

    # Accept both legacy and canonical field names in input
    @classmethod
    def model_validate(cls, data):
        # If only legacy fields are present, map them to canonical fields
        if "date" in data and "entry_date" not in data:
            data["entry_date"] = data["date"]
        if "reference" in data and "reference_number" not in data:
            data["reference_number"] = data["reference"]
        return super().model_validate(data)

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class JournalEntryCreate(JournalEntryBase):
    pass

class JournalEntryResponse(JournalEntryBase):
    id: UUID
    lines: List[JournalEntryLineResponse]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class JournalEntryListResponse(BaseModel):
    journal_entries: List[JournalEntryResponse]

class JournalEntryUpdate(BaseModel):
    company_id: Optional[UUID] = None
    entry_date: Optional[date] = None  # Renamed from 'date'
    description: Optional[str] = None
    reference_number: Optional[str] = None  # Renamed from 'reference'
    status: Optional[JournalEntryStatus] = None  # Use Enum for validation
    lines: Optional[List[JournalEntryLineCreate]] = None

# --- Fiscal Year/Period Schemas ---
class FiscalYearBase(BaseModel):
    company_id: UUID
    year_code: str
    start_date: date
    end_date: date
    is_closed: Optional[bool] = False

class FiscalYearCreate(FiscalYearBase):
    pass

class FiscalYearUpdate(BaseModel):
    year_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_closed: Optional[bool] = None

class FiscalYearResponse(FiscalYearBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FiscalYearListResponse(BaseModel):
    fiscal_years: List[FiscalYearResponse]

class FiscalPeriodBase(BaseModel):
    fiscal_year_id: UUID
    period_number: int
    period_name: str
    start_date: date
    end_date: date
    is_closed: Optional[bool] = False

class FiscalPeriodCreate(FiscalPeriodBase):
    pass

class FiscalPeriodUpdate(BaseModel):
    period_number: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_closed: Optional[bool] = None

class FiscalPeriodResponse(FiscalPeriodBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class FiscalPeriodListResponse(BaseModel):
    periods: List[FiscalPeriodResponse]

# --- Budget Schemas ---
class BudgetBase(BaseModel):
    company_id: UUID
    budget_name: str  # Use budget_name everywhere for clarity
    budget_code: str
    fiscal_year_id: UUID
    budget_type: BudgetType  # Use BudgetType enum for strict validation
    start_date: date  # Required
    end_date: date    # Required
    budget_currency_id: UUID  # Required
    status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    # Add other required fields as needed (see Budget model)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    budget_name: Optional[str] = None
    budget_code: Optional[str] = None
    budget_type: Optional[BudgetType] = None  # Use BudgetType for update as well
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_currency_id: Optional[UUID] = None
    status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    # Add other updatable fields as needed

class BudgetResponse(BudgetBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class BudgetListResponse(BaseModel):
    budgets: List[BudgetResponse]

# --- Budget Line, Approval, Allocation, Variance, AuditLog Schemas (minimal) ---
class BudgetLineBase(BaseModel):
    budget_id: Optional[UUID] = None  # <-- Make this optional for creation
    account_id: UUID
    line_number: int
    department_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    annual_budget_amount: Decimal
    original_budget_amount: Optional[Decimal] = None
    annual_budget_quantity: Optional[Decimal] = None
    budget_rate: Optional[Decimal] = None
    unit_of_measure: Optional[str] = None
    allocation_method: Optional[str] = None
    allocation_percentages: Optional[List[float]] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_locked: Optional[bool] = False
    locked_by: Optional[UUID] = None
    locked_date: Optional[datetime] = None

class BudgetLineCreate(BudgetLineBase):
    pass

class BudgetLineResponse(BudgetLineBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class BudgetApprovalBase(BaseModel):
    budget_id: UUID
    approval_level: int
    approver_id: UUID
    approver_name: str
    approver_role: Optional[str] = None
    approval_date: Optional[date] = None
    approval_status: str  # PENDING, APPROVED, REJECTED, DELEGATED
    comments: Optional[str] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_active: Optional[bool] = True
    # NOTE: Do NOT use 'status' here. Use 'approval_status' only.

class BudgetApprovalCreate(BudgetApprovalBase):
    pass

class BudgetApprovalResponse(BudgetApprovalBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class BudgetAllocationBase(BaseModel):
    budget_id: Optional[UUID] = None  # <-- Make this optional for creation
    source_budget_line_id: UUID
    allocation_name: str
    total_amount_to_allocate: Decimal
    allocation_method: str  # Should match AllocationMethod enum
    allocation_basis: Optional[str] = None
    description: Optional[str] = None
    allocation_rules: Optional[dict] = None
    status: Optional[str] = "PENDING"  # Should match ApprovalStatus enum
    executed_date: Optional[date] = None
    executed_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class BudgetAllocationCreate(BudgetAllocationBase):
    pass

class BudgetAllocationResponse(BudgetAllocationBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class BudgetVarianceBase(BaseModel):
    budget_line_id: UUID
    fiscal_period_id: UUID
    budget_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal
    variance_percentage: Decimal
    variance_type: VarianceType
    significance_level: SignificanceLevel
    variance_reason: Optional[str] = None
    corrective_action: Optional[str] = None

class BudgetVarianceCreate(BudgetVarianceBase):
    pass

class BudgetVarianceUpdate(BaseModel):
    budget_amount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    variance_amount: Optional[Decimal] = None
    variance_percentage: Optional[Decimal] = None
    variance_type: Optional[VarianceType] = None
    significance_level: Optional[SignificanceLevel] = None
    variance_reason: Optional[str] = None
    corrective_action: Optional[str] = None

class BudgetVarianceResponse(BudgetVarianceBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class BudgetVarianceListResponse(BaseModel):
    variances: List[BudgetVarianceResponse]
    total: int

class CurrencyBase(BaseModel):
    currency_code: str
    currency_name: str
    symbol: Optional[str] = None
    decimal_places: Optional[int] = 2
    is_active: Optional[bool] = True

class CurrencyCreate(CurrencyBase):
    pass

class CurrencyUpdate(BaseModel):
    currency_code: Optional[str] = None
    currency_name: Optional[str] = None
    symbol: Optional[str] = None
    decimal_places: Optional[Decimal] = None

class CurrencyResponse(CurrencyBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CurrencyListResponse(BaseModel):
    currencies: List[CurrencyResponse]
    total: int = 0

class BudgetPeriodLineBase(BaseModel):
    fiscal_period_id: UUID
    budget_amount: Decimal
    original_budget_amount: Optional[Decimal] = None
    budget_quantity: Optional[Decimal] = None
    budget_rate: Optional[Decimal] = None
    is_locked: Optional[bool] = False
    locked_by: Optional[UUID] = None
    locked_date: Optional[date] = None
    notes: Optional[str] = None

class BudgetPeriodLineCreate(BudgetPeriodLineBase):
    budget_line_id: UUID

class BudgetPeriodLineUpdate(BaseModel):
    fiscal_period_id: Optional[UUID] = None
    budget_amount: Optional[Decimal] = None
    original_budget_amount: Optional[Decimal] = None
    budget_quantity: Optional[Decimal] = None
    budget_rate: Optional[Decimal] = None
    is_locked: Optional[bool] = None
    locked_by: Optional[UUID] = None
    locked_date: Optional[date] = None
    notes: Optional[str] = None

class BudgetPeriodLineResponse(BudgetPeriodLineBase):
    id: UUID
    budget_line_id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class BudgetAllocationLineBase(BaseModel):
    allocation_id: Optional[UUID] = None  # <-- Make optional for creation
    target_budget_line_id: UUID
    allocation_percentage: Decimal
    allocated_amount: Decimal

class BudgetAllocationLineCreate(BudgetAllocationLineBase):
    pass

class BudgetAllocationLineUpdate(BaseModel):
    allocation_percentage: Optional[Decimal] = None
    allocated_amount: Optional[Decimal] = None
    target_budget_line_id: Optional[UUID] = None

class BudgetAllocationLineResponse(BudgetAllocationLineBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class BudgetAllocationLineListResponse(BaseModel):
    allocation_lines: List[BudgetAllocationLineResponse]
    total: int

# --- Budget Template Schemas ---
class BudgetTemplateBase(BaseModel):
    company_id: UUID
    template_name: str
    template_code: str
    budget_type: BudgetType
    template_data: dict
    default_allocation_method: AllocationMethod = AllocationMethod.EQUAL
    description: Optional[str] = None

class BudgetTemplateCreate(BudgetTemplateBase):
    pass

class BudgetTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    template_code: Optional[str] = None
    budget_type: Optional[BudgetType] = None
    template_data: Optional[dict] = None
    default_allocation_method: Optional[AllocationMethod] = None
    description: Optional[str] = None

class BudgetTemplateResponse(BudgetTemplateBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class BudgetTemplateListResponse(BaseModel):
    templates: List[BudgetTemplateResponse]
    total: int

class BudgetAuditLogBase(BaseModel):
    action: str
    performed_by: Optional[UUID] = None
    details: Optional[str] = None

class BudgetAuditLogCreate(BudgetAuditLogBase):
    pass

class BudgetAuditLogUpdate(BaseModel):
    action: Optional[str] = None
    performed_by: Optional[UUID] = None
    performed_at: Optional[date] = None
    details: Optional[str] = None

class BudgetAuditLogResponse(BudgetAuditLogBase):
    id: UUID
    budget_id: UUID
    performed_at: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class BudgetAuditLogListResponse(BaseModel):
    audit_logs: List[BudgetAuditLogResponse]
    total: int
    
class BudgetAuditLogSummaryResponse(BaseModel):
    budget_id: UUID
    action_counts: List[Dict[str, Any]]
    recent_activities: List[Dict[str, Any]]
