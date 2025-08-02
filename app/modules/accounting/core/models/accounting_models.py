from sqlalchemy import Column, String, Text, Numeric, Date, ForeignKey, JSON, Enum, Integer, Boolean, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.shared.models import BaseModel, Company, Currency, AccountCategory, AccountType, CenterType, ProfitCenterType, CostingMethod, EntryStatus
from app.shared.models import BudgetType, BudgetStatus, VersionType, AllocationMethod, ApprovalStatus, VarianceType, SignificanceLevel
import enum
import uuid
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from app.modules.accounting.config import AccountingEventTypes


SCHEMA = "accounting"

# =====================
# Org Chart Models
# =====================

class ProfitCenter(BaseModel):
    __tablename__ = "profit_centers"
    __table_args__ = {'schema': SCHEMA}

    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id", ondelete="CASCADE"), nullable=False)
    profit_center_code = Column(String(50), nullable=False, unique=True)
    profit_center_name = Column(String(200), nullable=False)
    name = Column(String(200), nullable=False)
    center_type = Column(PGEnum(ProfitCenterType, name="profitcentertype", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    parent_profit_center_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.profit_centers.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)

    company = relationship("Company", backref="profit_centers")
    parent_profit_center = relationship(
        "ProfitCenter",
        remote_side=lambda: [ProfitCenter.id],
        foreign_keys=[parent_profit_center_id],
        backref="child_profit_centers"
    )


class CostCenter(BaseModel):
    __tablename__ = "cost_centers"
    __table_args__ = {'schema': SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    parent_cost_center_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.cost_centers.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    profit_center_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.profit_centers.id"), nullable=True)
    # Add these fields to match the schema and API
    cost_center_code = Column(String(255), nullable=False)
    cost_center_name = Column(String(255), nullable=False)
    center_type = Column(
        PGEnum(
            CenterType,  # This should be the Enum class from app.shared.models
            name="centertype",
            create_type=False,  # Do not try to create the type, it already exists in DB
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False
    )

    company = relationship("Company", backref="cost_centers")
    profit_center = relationship("ProfitCenter", backref="cost_centers")
    parent_cost_center = relationship(
        "CostCenter",
        remote_side=lambda: [CostCenter.id],
        foreign_keys=[parent_cost_center_id],
        backref="child_cost_centers"
    )


# =====================
# Chart of Accounts (COA)
# =====================

class LedgerAccount(BaseModel):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint('account_code', 'company_id', name='uq_account_code_per_company'),
        {'schema': SCHEMA}
    )

    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id", ondelete="RESTRICT"), nullable=False)
    account_code = Column(String(20), nullable=False)
    account_name = Column(String(200), nullable=False)
    account_category = Column(Enum(AccountCategory), nullable=False)  # ASSETS, LIABILITIES, EQUITY, REVENUE, EXPENSES
    account_type = Column(Enum(AccountType), nullable=False)
    parent_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id", ondelete="SET NULL"))
    is_control_account = Column(Boolean, default=False)
    is_inter_company = Column(Boolean, default=False)
    cost_center_required = Column(Boolean, default=False)
    sku_tracking_enabled = Column(Boolean, default=False)
    consolidation_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id", ondelete="SET NULL"))
    elimination_account = Column(Boolean, default=False)

    company = relationship("Company")
    parent_account = relationship(
        "LedgerAccount",
        remote_side=lambda: [LedgerAccount.id],
        foreign_keys=[parent_account_id],
        backref="child_accounts"
    )


# =====================
# Journal Entry
# =====================

class JournalEntry(BaseModel):
    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint('entry_number', 'company_id', name='uq_entry_number_per_company'),
        {'schema': SCHEMA}
    )

    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id", ondelete="CASCADE"), nullable=False)
    entry_number = Column(String(50), nullable=False)
    entry_date = Column(Date, nullable=False)
    fiscal_period_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.fiscal_periods.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)
    source_document = Column(String(100), nullable=True)
    total_debit = Column(Numeric(18, 2), nullable=False, default=0)
    total_credit = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(Enum(EntryStatus), default=EntryStatus.DRAFT)
    posted_date = Column(Date, nullable=True)

    company = relationship("Company", backref="journal_entries")
    fiscal_period = relationship("FiscalPeriod")
    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalEntryLine(BaseModel):
    __tablename__ = "journal_entry_lines"
    __table_args__ = {'schema': SCHEMA}

    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.journal_entries.id", ondelete="CASCADE"), nullable=False)
    line_number = Column(Integer, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id", ondelete="RESTRICT"), nullable=False)
    debit_amount = Column(Numeric(15, 2), default=0)
    credit_amount = Column(Numeric(15, 2), default=0)
    functional_currency_amount = Column(Numeric(15, 2), nullable=True)
    reporting_currency_amount = Column(Numeric(15, 2), nullable=True)
    exchange_rate = Column(Numeric(15, 6), nullable=True)
    cost_center_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.cost_centers.id", ondelete="SET NULL"), nullable=True)
    profit_center_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.profit_centers.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=True)
    inventory_transaction_id = Column(UUID(as_uuid=True), nullable=True)  # FK temporarily removed
    sku_id = Column(UUID(as_uuid=True), nullable=True)  # FK temporarily removed

    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("LedgerAccount")
    cost_center = relationship("CostCenter")
    profit_center = relationship("ProfitCenter")
    company = relationship("Company")
    # Optionally, add relationships to inventory models if needed
    # stock_movement = relationship("StockMovement")
    # product = relationship("Product")


class FiscalYear(BaseModel):
    __tablename__ = "fiscal_years"
    __table_args__ = {'schema': SCHEMA}

    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id", ondelete="RESTRICT"), nullable=False)
    year_code = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_closed = Column(Boolean, default=False)

    company = relationship("Company", back_populates="fiscal_years")
    periods = relationship("FiscalPeriod", back_populates="fiscal_year")

    # Event bus events:
    #   - Trigger 'fiscalyear.created' on creation
    #   - Trigger 'fiscalyear.closed' when is_closed is set to True
    #   - Trigger 'fiscalyear.updated' on update


class FiscalPeriod(BaseModel):
    __tablename__ = "fiscal_periods"
    __table_args__ = {'schema': SCHEMA}

    fiscal_year_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.fiscal_years.id", ondelete="CASCADE"), nullable=False)
    period_number = Column(Integer, nullable=False)
    period_name = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_closed = Column(Boolean, default=False)

    fiscal_year = relationship("FiscalYear", back_populates="periods")

    # Event bus events:
    #   - Trigger 'fiscalperiod.created' on creation
    #   - Trigger 'fiscalperiod.closed' when is_closed is set to True
    #   - Trigger 'fiscalperiod.updated' on update


class Budget(BaseModel):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint('budget_code', 'company_id', 'fiscal_year_id', name='uq_budget_code_per_company_year'),
        {'schema': SCHEMA}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)
    budget_name = Column(String(200), nullable=False)
    budget_code = Column(String(50), nullable=False)
    budget_type = Column(Enum(BudgetType), nullable=False)
    fiscal_year_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.fiscal_years.id"), nullable=False)
    budget_version = Column(String(20), default="1.0")
    version_type = Column(Enum(VersionType), default=VersionType.ORIGINAL)
    parent_budget_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budgets.id"))
    status = Column(Enum(BudgetStatus), default=BudgetStatus.DRAFT)
    submitted_by = Column(UUID(as_uuid=True))
    submitted_date = Column(Date)
    approved_by = Column(UUID(as_uuid=True))
    approved_date = Column(Date)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget_currency_id = Column(UUID(as_uuid=True), ForeignKey("public.currencies.id"), nullable=False)
    allow_line_item_changes = Column(Boolean, default=True)
    auto_allocate_periods = Column(Boolean, default=True)
    allocation_method = Column(Enum(AllocationMethod), default=AllocationMethod.EQUAL)
    description = Column(Text)
    assumptions = Column(Text)
    notes = Column(Text)
    tags = Column(JSON)

    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"))
    updated_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"))
    created_at = Column(Date, server_default=func.now())
    updated_at = Column(Date, onupdate=func.now())
    is_locked = Column(Boolean, default=False)
    locked_by = Column(UUID(as_uuid=True))
    locked_date = Column(Date)

    company = relationship("Company")
    fiscal_year = relationship("FiscalYear")
    currency = relationship("Currency")
    parent_budget = relationship(
        "Budget",
        remote_side=lambda: [Budget.id],
        foreign_keys=[parent_budget_id],
        backref="sub_budgets"
    )
    budget_lines = relationship("BudgetLine", back_populates="budget", cascade="all, delete-orphan")
    budget_approvals = relationship("BudgetApproval", back_populates="budget", cascade="all, delete-orphan")



class BudgetLine(BaseModel):
    __tablename__ = "budget_lines"
    __table_args__ = {'schema': SCHEMA}

    budget_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budgets.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("public.departments.id"))
    project_id = Column(UUID(as_uuid=True))
    annual_budget_amount = Column(Numeric(15, 2), nullable=False)
    original_budget_amount = Column(Numeric(15, 2))
    annual_budget_quantity = Column(Numeric(15, 4))
    budget_rate = Column(Numeric(15, 4))
    unit_of_measure = Column(String(20))
    allocation_method = Column(Enum(AllocationMethod), default=AllocationMethod.EQUAL)
    allocation_percentages = Column(JSON)
    description = Column(Text)
    notes = Column(Text)

    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"))
    updated_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"))
    created_at = Column(Date, server_default=func.now())
    updated_at = Column(Date, onupdate=func.now())
    is_locked = Column(Boolean, default=False)
    locked_by = Column(UUID(as_uuid=True))
    locked_date = Column(Date)

    budget = relationship("Budget", back_populates="budget_lines")
    account = relationship("app.modules.accounting.core.models.accounting_models.LedgerAccount")
    department = relationship("Department")
    period_lines = relationship("BudgetPeriodLine", back_populates="budget_line", cascade="all, delete-orphan")


class BudgetPeriodLine(BaseModel):
    __tablename__ = "budget_period_lines"
    __table_args__ = {'schema': SCHEMA}

    budget_line_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budget_lines.id"), nullable=False)
    fiscal_period_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.fiscal_periods.id"), nullable=False)
    budget_amount = Column(Numeric(15, 2), nullable=False)
    original_budget_amount = Column(Numeric(15, 2))
    budget_quantity = Column(Numeric(15, 4))
    budget_rate = Column(Numeric(15, 4))
    is_locked = Column(Boolean, default=False)
    locked_by = Column(UUID(as_uuid=True))
    locked_date = Column(Date)
    notes = Column(Text)

    budget_line = relationship("BudgetLine", back_populates="period_lines")
    fiscal_period = relationship("FiscalPeriod")


class BudgetApproval(BaseModel):
    __tablename__ = "budget_approvals"
    __table_args__ = {'schema': SCHEMA}

    budget_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budgets.id"), nullable=False)
    approval_level = Column(Integer, nullable=False)
    approver_id = Column(UUID(as_uuid=True), nullable=False)
    approver_name = Column(String(200), nullable=False)
    approver_role = Column(String(100))
    approval_date = Column(Date)
    approval_status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    comments = Column(Text)

    budget = relationship("Budget", back_populates="budget_approvals")


class BudgetAllocation(BaseModel):
    __tablename__ = "budget_allocations"
    __table_args__ = {'schema': SCHEMA}

    budget_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budgets.id"), nullable=False)
    source_budget_line_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budget_lines.id"), nullable=False)
    allocation_name = Column(String(200), nullable=False)
    total_amount_to_allocate = Column(Numeric(15, 2), nullable=False)
    allocation_method = Column(Enum(AllocationMethod), default=AllocationMethod.EQUAL)
    allocation_basis = Column(String(100))
    description = Column(Text)
    allocation_rules = Column(JSON)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    executed_date = Column(Date)
    executed_by = Column(UUID(as_uuid=True))

    budget = relationship("Budget")
    source_budget_line = relationship("BudgetLine")
    allocation_lines = relationship("BudgetAllocationLine", back_populates="allocation", cascade="all, delete-orphan")


class BudgetAllocationLine(BaseModel):
    __tablename__ = "budget_allocation_lines"
    __table_args__ = {'schema': SCHEMA}

    allocation_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budget_allocations.id"), nullable=False)
    target_budget_line_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budget_lines.id"), nullable=False)
    allocation_percentage = Column(Numeric(5, 2), nullable=False)
    allocated_amount = Column(Numeric(15, 2), nullable=False)

    allocation = relationship("BudgetAllocation", back_populates="allocation_lines")
    target_budget_line = relationship("BudgetLine")


class BudgetTemplate(BaseModel):
    __tablename__ = "budget_templates"
    __table_args__ = {'schema': SCHEMA}

    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)
    template_name = Column(String(200), nullable=False)
    template_code = Column(String(50), nullable=False)
    budget_type = Column(Enum(BudgetType), nullable=False)
    template_data = Column(JSON, nullable=False)
    default_allocation_method = Column(Enum(AllocationMethod), default=AllocationMethod.EQUAL)
    description = Column(Text)

    company = relationship("Company")


class BudgetVariance(BaseModel):
    __tablename__ = "budget_variances"
    __table_args__ = {'schema': SCHEMA}

    budget_line_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budget_lines.id"), nullable=False)
    fiscal_period_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.fiscal_periods.id"), nullable=False)
    budget_amount = Column(Numeric(15, 2), nullable=False)
    actual_amount = Column(Numeric(15, 2), nullable=False)
    variance_amount = Column(Numeric(15, 2), nullable=False)
    variance_percentage = Column(Numeric(5, 2), nullable=False)
    variance_type = Column(Enum(VarianceType), nullable=False)
    significance_level = Column(Enum(SignificanceLevel), nullable=False)
    variance_reason = Column(Text)
    corrective_action = Column(Text)

    budget_line = relationship("BudgetLine")
    fiscal_period = relationship("FiscalPeriod")


class BudgetAuditLog(BaseModel):
    __tablename__ = "budget_audit_log"
    __table_args__ = {'schema': SCHEMA}

    budget_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.budgets.id"), nullable=False)
    action = Column(String(50), nullable=False)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"))
    performed_at = Column(Date, server_default=func.now())
    details = Column(Text)






