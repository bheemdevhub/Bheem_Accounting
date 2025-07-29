# app/modules/accounting/core/models/enhanced_financial_models.py
"""
Enhanced Financial Management Models
Complete the finance cycle with AP/AR, Payments, Assets, etc.
"""

from sqlalchemy import (
    Column, String, Text, Numeric, Date, ForeignKey, Boolean, Integer, DateTime,
    Enum as SQLEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, object_session
from sqlalchemy.sql import func
from app.shared.models import BaseModel
import enum
import uuid

SCHEMA = "accounting"

# =============================================
# Enums
# =============================================

class InvoiceType(str, enum.Enum):
    SALES_INVOICE = "SALES_INVOICE"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"
    PROFORMA = "PROFORMA"

class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SENT = "SENT"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    FULLY_PAID = "FULLY_PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    VOID = "VOID"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    CLEARED = "CLEARED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RECONCILED = "RECONCILED"

class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    CHECK = "CHECK"
    CREDIT_CARD = "CREDIT_CARD"
    ELECTRONIC = "ELECTRONIC"
    WIRE_TRANSFER = "WIRE_TRANSFER"

class AssetType(str, enum.Enum):
    LAND = "LAND"
    BUILDING = "BUILDING"
    MACHINERY = "MACHINERY"
    EQUIPMENT = "EQUIPMENT"
    VEHICLE = "VEHICLE"
    FURNITURE = "FURNITURE"
    IT_EQUIPMENT = "IT_EQUIPMENT"
    INTANGIBLE = "INTANGIBLE"

class DepreciationMethod(str, enum.Enum):
    STRAIGHT_LINE = "STRAIGHT_LINE"
    DECLINING_BALANCE = "DECLINING_BALANCE"
    UNITS_OF_PRODUCTION = "UNITS_OF_PRODUCTION"
    SUM_OF_YEARS = "SUM_OF_YEARS"

# =============================================
# Models
# =============================================

class Invoice(BaseModel):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint('invoice_number', 'company_id', name='uq_invoice_number_per_company'),
        Index('ix_invoices_customer', 'customer_id'),
        Index('ix_invoices_supplier', 'supplier_id'),
        Index('ix_invoices_status', 'status'),
        Index('ix_invoices_due_date', 'due_date'),
        {'schema': SCHEMA}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)
    invoice_number = Column(String(50), nullable=False)
    invoice_type = Column(SQLEnum(InvoiceType, name="invoicetype_enum", create_type=False), nullable=False)
    status = Column(SQLEnum(InvoiceStatus, name="invoicestatus_enum", create_type=False), nullable=False, default=InvoiceStatus.DRAFT)

    invoice_date = Column(Date, nullable=False, default=func.current_date())
    due_date = Column(Date, nullable=False)
    service_period_start = Column(Date)
    service_period_end = Column(Date)

    customer_id = Column(UUID(as_uuid=True), ForeignKey("sales.customers.id"))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("purchase.suppliers.id"))

    reference_type = Column(String(50))
    reference_id = Column(UUID(as_uuid=True))
    reference_number = Column(String(50))

    currency = Column(String(3), default="USD")
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    subtotal = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=0)
    discount_amount = Column(Numeric(15, 2), default=0)
    shipping_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)
    paid_amount = Column(Numeric(15, 2), default=0)
    balance_due = Column(Numeric(15, 2))

    payment_terms_days = Column(Integer, default=30)
    discount_terms = Column(String(50))

    ar_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    ap_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    journal_entry_id = Column(UUID(as_uuid=True))

    created_by = Column(UUID(as_uuid=True), ForeignKey("public.persons.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("public.persons.id"))
    approved_date = Column(Date)

    notes = Column(Text)
    terms_and_conditions = Column(Text)

    invoice_lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")

    def calculate_aging_days(self):
        from datetime import date
        if self.status == InvoiceStatus.FULLY_PAID:
            return 0
        today = date.today()
        return (today - self.due_date).days if today > self.due_date else 0

class InvoiceLine(BaseModel):
    __tablename__ = "invoice_lines"
    __table_args__ = {'schema': SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.invoices.id"), nullable=False)
    line_number = Column(Integer, nullable=False)

    product_id = Column(UUID(as_uuid=True), ForeignKey("inventory.products.id"))
    item_code = Column(String(50))
    item_description = Column(String(255), nullable=False)

    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit_price = Column(Numeric(15, 4), nullable=False)
    discount_percentage = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(15, 2), default=0)
    line_total = Column(Numeric(15, 2), nullable=False)

    tax_code = Column(String(20))
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)

    revenue_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    expense_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    cost_center_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.cost_centers.id"))

    notes = Column(Text)
    invoice = relationship("Invoice", back_populates="invoice_lines")

class Payment(BaseModel):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint('payment_number', 'company_id', name='uq_payment_number_per_company'),
        Index('ix_payments_invoice', 'invoice_id'),
        Index('ix_payments_status', 'status'),
        Index('ix_payments_method', 'payment_method'),
        {'schema': SCHEMA}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)
    payment_number = Column(String(50), nullable=False)
    payment_date = Column(Date, nullable=False, default=func.current_date())

    invoice_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.invoices.id"))

    payment_method = Column(SQLEnum(PaymentMethod, name="paymentmethod_enum", create_type=False), nullable=False)
    payment_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    exchange_rate = Column(Numeric(10, 6), default=1.0)

    status = Column(SQLEnum(PaymentStatus, name="paymentstatus_enum", create_type=False), nullable=False, default=PaymentStatus.PENDING)

    bank_account_id = Column(UUID(as_uuid=True), ForeignKey("public.bank_accounts.id"))
    check_number = Column(String(50))
    transaction_reference = Column(String(100))

    cash_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    journal_entry_id = Column(UUID(as_uuid=True))

    processed_by = Column(UUID(as_uuid=True), ForeignKey("public.persons.id"))
    processed_date = Column(DateTime)
    reconciled_date = Column(Date)

    notes = Column(Text)
    invoice = relationship("Invoice", back_populates="payments")

class FixedAsset(BaseModel):
    __tablename__ = "fixed_assets"
    __table_args__ = (
        UniqueConstraint('asset_code', 'company_id', name='uq_asset_code_per_company'),
        Index('ix_fixed_assets_type', 'asset_type'),
        Index('ix_fixed_assets_location', 'location_id'),
        {'schema': SCHEMA}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)
    asset_code = Column(String(50), nullable=False)
    asset_name = Column(String(255), nullable=False)
    asset_type = Column(SQLEnum(AssetType, name="asset_type_enum", create_type=False), nullable=False)

    description = Column(Text)
    manufacturer = Column(String(100))
    model = Column(String(100))
    serial_number = Column(String(100))

    purchase_date = Column(Date, nullable=False)
    purchase_cost = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")

    depreciation_method = Column(SQLEnum(DepreciationMethod, name="depreciation_method_enum", create_type=False), nullable=False)
    useful_life_years = Column(Integer, nullable=False)
    useful_life_units = Column(Integer)
    salvage_value = Column(Numeric(15, 2), default=0)

    accumulated_depreciation = Column(Numeric(15, 2), default=0)
    net_book_value = Column(Numeric(15, 2))
    fair_market_value = Column(Numeric(15, 2))

    location_id = Column(UUID(as_uuid=True), ForeignKey("inventory.warehouses.id"))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("public.persons.id"))
    cost_center_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.cost_centers.id"))

    asset_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False)
    depreciation_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    accumulated_depreciation_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))

    status = Column(String(20), default="ACTIVE")
    disposal_date = Column(Date)
    disposal_value = Column(Numeric(15, 2))
    last_maintenance_date = Column(Date)
    next_maintenance_date = Column(Date)
    notes = Column(Text)

    depreciation_schedule = relationship("DepreciationSchedule", back_populates="asset", cascade="all, delete-orphan")

class DepreciationSchedule(BaseModel):
    __tablename__ = "depreciation_schedule"
    __table_args__ = (
        Index('ix_depreciation_schedule_asset', 'asset_id'),
        Index('ix_depreciation_schedule_period', 'period_date'),
        {'schema': SCHEMA}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.fixed_assets.id"), nullable=False)
    period_date = Column(Date, nullable=False)
    beginning_book_value = Column(Numeric(15, 2), nullable=False)
    depreciation_amount = Column(Numeric(15, 2), nullable=False)
    accumulated_depreciation = Column(Numeric(15, 2), nullable=False)
    ending_book_value = Column(Numeric(15, 2), nullable=False)
    is_posted = Column(Boolean, default=False)
    journal_entry_id = Column(UUID(as_uuid=True))
    posted_date = Column(Date)
    asset = relationship("FixedAsset", back_populates="depreciation_schedule")

class TaxCode(BaseModel):
    __tablename__ = "tax_codes"
    __table_args__ = (
        UniqueConstraint('tax_code', 'company_id', name='uq_tax_code_per_company'),
        {'schema': SCHEMA}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)
    tax_code = Column(String(20), nullable=False)
    tax_name = Column(String(100), nullable=False)
    tax_rate = Column(Numeric(5, 4), nullable=False)
    tax_type = Column(String(50))
    tax_payable_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    tax_receivable_account_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.accounts.id"))
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
