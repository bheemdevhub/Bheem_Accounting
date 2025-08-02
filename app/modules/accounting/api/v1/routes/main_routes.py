from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.accounting.core.services.accounting_service import FiscalYearService, FiscalPeriodService, CompanyService, CurrencyService
from app.modules.accounting.core.schemas.accounting_schemas import (
    FiscalYearCreate, FiscalYearUpdate, FiscalYearResponse, FiscalYearListResponse,
    FiscalPeriodCreate, FiscalPeriodUpdate, FiscalPeriodResponse, FiscalPeriodListResponse,
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse,
    CurrencyCreate, CurrencyUpdate, CurrencyResponse, CurrencyListResponse
)
from app.modules.auth.core.services.permissions_service import get_current_user, require_roles, require_api_permission

# Try to import from bheem_core, fallback to local stubs if not available
try:
    from bheem_core.shared.models import UserRole
    from bheem_core.database import get_db
except ImportError:
    from app.core.bheem_core_stubs import UserRole, get_db
from uuid import UUID
from typing import List
from fastapi.responses import Response

fiscal_router = APIRouter(prefix="/fiscal-years", tags=["Fiscal Years"])
fiscal_period_router = APIRouter(prefix="/fiscal-periods", tags=["Fiscal Periods"])
company_router = APIRouter(prefix="/companies", tags=["Companies"])
currency_router = APIRouter(prefix="/currencies", tags=["Currencies"])

@fiscal_router.post("/", response_model=FiscalYearResponse, status_code=201, dependencies=[Depends(lambda: require_api_permission("fiscalyear.create"))])
async def create_fiscal_year(
    data: FiscalYearCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalYearService(db)
    fiscal_year = await service.create_fiscal_year(data)
    return FiscalYearResponse.model_validate(fiscal_year, from_attributes=True)

@fiscal_router.get("/", response_model=FiscalYearListResponse, dependencies=[Depends(lambda: require_api_permission("fiscalyear.read"))])
async def list_fiscal_years(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalYearService(db)
    fiscal_years = await service.list_fiscal_years(skip=skip, limit=limit)
    return FiscalYearListResponse(fiscal_years=[FiscalYearResponse.model_validate(f, from_attributes=True) for f in fiscal_years], total=len(fiscal_years))

@fiscal_router.get("/{fiscal_year_id}", response_model=FiscalYearResponse, dependencies=[Depends(lambda: require_api_permission("fiscalyear.read"))])
async def get_fiscal_year(
    fiscal_year_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalYearService(db)
    fiscal_year = await service.get_fiscal_year(fiscal_year_id)
    return FiscalYearResponse.model_validate(fiscal_year, from_attributes=True)

@fiscal_router.put("/{fiscal_year_id}", response_model=FiscalYearResponse, dependencies=[Depends(lambda: require_api_permission("fiscalyear.update"))])
async def update_fiscal_year(
    fiscal_year_id: UUID,
    data: FiscalYearUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalYearService(db)
    fiscal_year = await service.update_fiscal_year(fiscal_year_id, data)
    return FiscalYearResponse.model_validate(fiscal_year, from_attributes=True)

@fiscal_router.delete("/{fiscal_year_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(lambda: require_api_permission("fiscalyear.delete"))])
async def delete_fiscal_year(
    fiscal_year_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalYearService(db)
    await service.delete_fiscal_year(fiscal_year_id)
    return None

# FiscalPeriod endpoints

@fiscal_period_router.post("/", response_model=FiscalPeriodResponse, status_code=201, dependencies=[Depends(lambda: require_api_permission("fiscalperiod.create"))])
async def create_fiscal_period(
    data: FiscalPeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalPeriodService(db)
    fiscal_period = await service.create_fiscal_period(data)
    return FiscalPeriodResponse.model_validate(fiscal_period, from_attributes=True)

@fiscal_period_router.get("/", response_model=FiscalPeriodListResponse, dependencies=[Depends(lambda: require_api_permission("fiscalperiod.read"))])
async def list_fiscal_periods(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalPeriodService(db)
    fiscal_periods = await service.list_fiscal_periods(skip=skip, limit=limit)
    return FiscalPeriodListResponse(fiscal_periods=[FiscalPeriodResponse.model_validate(f, from_attributes=True) for f in fiscal_periods], total=len(fiscal_periods))

@fiscal_period_router.get("/{fiscal_period_id}", response_model=FiscalPeriodResponse, dependencies=[Depends(lambda: require_api_permission("fiscalperiod.read"))])
async def get_fiscal_period(
    fiscal_period_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalPeriodService(db)
    fiscal_period = await service.get_fiscal_period(fiscal_period_id)
    return FiscalPeriodResponse.model_validate(fiscal_period, from_attributes=True)

@fiscal_period_router.put("/{fiscal_period_id}", response_model=FiscalPeriodResponse, dependencies=[Depends(lambda: require_api_permission("fiscalperiod.update"))])
async def update_fiscal_period(
    fiscal_period_id: UUID,
    data: FiscalPeriodUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalPeriodService(db)
    fiscal_period = await service.update_fiscal_period(fiscal_period_id, data)
    return FiscalPeriodResponse.model_validate(fiscal_period, from_attributes=True)

@fiscal_period_router.delete("/{fiscal_period_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(lambda: require_api_permission("fiscalperiod.delete"))])
async def delete_fiscal_period(
    fiscal_period_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = FiscalPeriodService(db)
    await service.delete_fiscal_period(fiscal_period_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Company CRUD

@company_router.post("/", response_model=CompanyResponse, status_code=201, dependencies=[Depends(lambda: require_api_permission("company.create"))])
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CompanyService(db)
    company = await service.create_company(data)
    return CompanyResponse.model_validate(company, from_attributes=True)

@company_router.get("/", response_model=CompanyListResponse, dependencies=[Depends(lambda: require_api_permission("company.read"))])
async def list_companies(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CompanyService(db)
    companies = await service.list_companies(skip=skip, limit=limit)
    return CompanyListResponse(companies=[CompanyResponse.model_validate(c, from_attributes=True) for c in companies], total=len(companies))

@company_router.get("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(lambda: require_api_permission("company.read"))])
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CompanyService(db)
    company = await service.get_company(company_id)
    return CompanyResponse.model_validate(company, from_attributes=True)

@company_router.put("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(lambda: require_api_permission("company.update"))])
async def update_company(
    company_id: UUID,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CompanyService(db)
    company = await service.update_company(company_id, data)
    return CompanyResponse.model_validate(company, from_attributes=True)

@company_router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(lambda: require_api_permission("company.delete"))])
async def delete_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CompanyService(db)
    await service.delete_company(company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Currency CRUD

@currency_router.post("/", response_model=CurrencyResponse, status_code=201, dependencies=[Depends(lambda: require_api_permission("currency.create"))])
async def create_currency(
    data: CurrencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CurrencyService(db)
    currency = await service.create_currency(data)
    return CurrencyResponse.model_validate(currency, from_attributes=True)

@currency_router.get("/", response_model=CurrencyListResponse, dependencies=[Depends(lambda: require_api_permission("currency.read"))])
async def list_currencies(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CurrencyService(db)
    currencies = await service.list_currencies(skip=skip, limit=limit)
    return CurrencyListResponse(currencies=[CurrencyResponse.model_validate(c, from_attributes=True) for c in currencies], total=len(currencies))

@currency_router.get("/{currency_id}", response_model=CurrencyResponse, dependencies=[Depends(lambda: require_api_permission("currency.read"))])
async def get_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CurrencyService(db)
    currency = await service.get_currency(currency_id)
    return CurrencyResponse.model_validate(currency, from_attributes=True)

@currency_router.put("/{currency_id}", response_model=CurrencyResponse, dependencies=[Depends(lambda: require_api_permission("currency.update"))])
async def update_currency(
    currency_id: UUID,
    data: CurrencyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CurrencyService(db)
    currency = await service.update_currency(currency_id, data)
    return CurrencyResponse.model_validate(currency, from_attributes=True)

@currency_router.delete("/{currency_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(lambda: require_api_permission("currency.delete"))])
async def delete_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CurrencyService(db)
    await service.delete_currency(currency_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Register routers
router = APIRouter()
router.include_router(fiscal_router)
router.include_router(fiscal_period_router)
router.include_router(company_router)
router.include_router(currency_router)
# Add new routers for accounts and cost centers
from app.modules.accounting.api.v1.routes.accounting_crud_routes import account_router, cost_center_router
router.include_router(account_router)
router.include_router(cost_center_router)
