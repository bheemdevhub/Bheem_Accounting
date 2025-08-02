"""Mock models for production deployment"""

from sqlalchemy import Column, String, Boolean, Text, DateTime, Date, ForeignKey, func, Table, Numeric, JSON, Enum, UniqueConstraint, Index, Integer, DECIMAL
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLAEnum

# Create a base for this mock
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class EntityTypes(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    LEAD = "LEAD"
    EMPLOYEE = "EMPLOYEE"
    VENDOR = "VENDOR"
    PROJECT = "PROJECT"
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    SKU = "SKU"
    ACTIVITY = "ACTIVITY"
    DOCUMENT = "DOCUMENT"
    TAG = "TAG"
    RATING = "RATING"

class CompanyType(enum.Enum):
    HOLDING = "HOLDING"
    SUBSIDIARY = "SUBSIDIARY"
    OPERATING = "OPERATING"
    JOINT_VENTURE = "JOINT_VENTURE"

class ConsolidationMethod(enum.Enum):
    FULL = "FULL"
    PROPORTIONAL = "PROPORTIONAL"
    EQUITY = "EQUITY"

class Gender(enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

class MaritalStatus(enum.Enum):
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    SEPARATED = "separated"
    OTHER = "other"

class BaseModel(Base):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))
    is_active = Column(Boolean, default=True)

class Company(BaseModel):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint('company_code', name='uq_company_code'),
        {'schema': 'public'}
    )
    
    company_code = Column(String(20), unique=True, nullable=False)
    company_name = Column(String(200), nullable=False)
    legal_name = Column(String(300))
    company_type = Column(Enum(CompanyType, name="companytype", create_type=False), nullable=False)
    parent_company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"))
    
    functional_currency_id = Column(UUID(as_uuid=True), ForeignKey("public.currencies.id"))
    reporting_currency_id = Column(UUID(as_uuid=True), ForeignKey("public.currencies.id"))
    consolidation_method = Column(Enum(ConsolidationMethod, name="consolidationmethod", create_type=False), default=ConsolidationMethod.FULL)
    
    address = Column(Text)
    tax_id = Column(String(50))
    registration_number = Column(String(50))

    parent_company = relationship(
        "Company",
        remote_side=lambda: [Company.id],
        foreign_keys=[parent_company_id],
        backref="subsidiaries"
    )

class Currency(BaseModel):
    __tablename__ = "currencies"
    __table_args__ = (
        UniqueConstraint('currency_code', name='uq_currency_code'),
        Index('ix_currency_code', 'currency_code'),
        {'schema': 'public'}
    )

    currency_code = Column(String(3), nullable=False)  # e.g., USD, INR
    currency_name = Column(String(100), nullable=False)
    symbol = Column(String(10))
    decimal_places = Column(Numeric(2), default=2)

class Person(BaseModel):
    __tablename__ = "persons"
    __table_args__ = {'schema': 'public'}
    
    person_type = Column(String(20), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    preferred_name = Column(String(100), nullable=True)
    title = Column(String(20), nullable=True)
    suffix = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(PGEnum(Gender, name="gender_enum", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=True)
    marital_status = Column(PGEnum(MaritalStatus, name="marital_status_enum", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=True)
    nationality = Column(String(100), nullable=True)
    blood_group = Column(String(10), nullable=True)
    supabase_id = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'person',
        'polymorphic_on': person_type
    }

# Add any other essential models that might be imported
class Address(BaseModel):
    __tablename__ = "addresses"
    __table_args__ = {'schema': 'public'}
    
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    address_type = Column(String(20), default="PRIMARY")
    line1 = Column(String(255), nullable=False)
    line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="USA")

class Contact(BaseModel):
    __tablename__ = "contacts"
    __table_args__ = {'schema': 'public'}

    person_id = Column(UUID(as_uuid=True), ForeignKey("public.persons.id"), nullable=False)
    email_primary = Column(String(100), nullable=True)
    email_secondary = Column(String(100), nullable=True)
    phone_primary = Column(String(20), nullable=True)
    phone_secondary = Column(String(20), nullable=True)
    phone_mobile = Column(String(20), nullable=True)
    phone_work = Column(String(20), nullable=True)
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)

    person = relationship("Person", back_populates="contacts")
