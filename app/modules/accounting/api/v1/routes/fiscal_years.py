# app/modules/accounting/api/v1/routes/fiscal_years.py
"""Fiscal Year and Periods API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.accounting.core.schemas.accounting_schemas import FiscalYearCreate, FiscalYearUpdate, FiscalYearResponse, FiscalYearListResponse, FiscalPeriodCreate, FiscalPeriodUpdate, FiscalPeriodResponse
from app.modules.accounting.core.services.accounting_service import FiscalYearService
from bheem_core.database import get_db
from app.modules.auth.core.services.permissions_service import require_roles, require_api_permission
from functools import partial
from bheem_core.event_bus import EventBus
from app.modules.accounting.config import AccountingEventTypes
from typing import List

router = APIRouter(prefix="/fiscal-years", tags=["Fiscal Years"])

def get_fiscal_year_service(db: AsyncSession = Depends(get_db)):
    # Pass event bus to service for event publishing
    return FiscalYearService(db, event_bus=EventBus())

def permission_dep(permission_code: str):
    return Depends(partial(require_api_permission, permission_code=permission_code))

@router.get("/", response_model=FiscalYearListResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), permission_dep("accounting.view_fiscal_year")])
async def list_fiscal_years(skip: int = 0, limit: int = 100, service: FiscalYearService = Depends(get_fiscal_year_service)):
    fiscal_years = await service.list_fiscal_years(skip=skip, limit=limit)
    # Convert ORM objects to Pydantic schemas for response
    return FiscalYearListResponse(fiscal_years=[FiscalYearResponse.model_validate(fy, from_attributes=True) for fy in fiscal_years])

@router.post("/", response_model=FiscalYearResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin")), permission_dep("accounting.create_fiscal_year")])
async def create_fiscal_year(fiscal_year: FiscalYearCreate, service: FiscalYearService = Depends(get_fiscal_year_service)):
    created = await service.create_fiscal_year(fiscal_year)
    # Publish event after creation
    await service.event_bus.publish(AccountingEventTypes.FISCAL_YEAR_CREATED, {"fiscal_year_id": str(created.id)})
    return created

@router.get("/{fiscal_year_id}", response_model=FiscalYearResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), permission_dep("accounting.view_fiscal_year")])
async def get_fiscal_year(fiscal_year_id: UUID, service: FiscalYearService = Depends(get_fiscal_year_service)):
    fiscal_year = await service.get_fiscal_year(fiscal_year_id)
    return fiscal_year

@router.put("/{fiscal_year_id}", response_model=FiscalYearResponse, dependencies=[Depends(require_roles("Accountant", "Admin")), permission_dep("accounting.update_fiscal_year")])
async def update_fiscal_year(fiscal_year_id: UUID, fiscal_year: FiscalYearUpdate, service: FiscalYearService = Depends(get_fiscal_year_service)):
    updated, closed = await service.update_fiscal_year(fiscal_year_id, fiscal_year)
    # Publish update event
    await service.event_bus.publish(AccountingEventTypes.FISCAL_YEAR_UPDATED, {"fiscal_year_id": str(fiscal_year_id)})
    if closed:
        await service.event_bus.publish(AccountingEventTypes.FISCAL_YEAR_CLOSED, {"fiscal_year_id": str(fiscal_year_id)})
    return updated

@router.delete("/{fiscal_year_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), permission_dep("accounting.delete_fiscal_year")])
async def delete_fiscal_year(fiscal_year_id: UUID, service: FiscalYearService = Depends(get_fiscal_year_service)):
    await service.delete_fiscal_year(fiscal_year_id)
    # Optionally publish delete event
    return None

@router.get("/{fiscal_year_id}/periods", summary="List periods for a fiscal year", response_model=List[FiscalPeriodResponse])
async def list_periods(fiscal_year_id: UUID, service: FiscalYearService = Depends(get_fiscal_year_service)):
    periods = await service.list_periods(fiscal_year_id)
    return [FiscalPeriodResponse.from_orm(p) for p in periods]

@router.post("/{fiscal_year_id}/periods", summary="Create period", response_model=FiscalPeriodResponse)
async def create_period(
    fiscal_year_id: UUID,
    period: FiscalPeriodCreate,  # Use Pydantic model, not dict
    service: FiscalYearService = Depends(get_fiscal_year_service)
):
    created = await service.create_period(fiscal_year_id, period)  # Pass Pydantic model directly
    return FiscalPeriodResponse.from_orm(created)

@router.put("/{fiscal_year_id}/periods/{period_id}", summary="Update period", response_model=FiscalPeriodResponse)
async def update_period(
    fiscal_year_id: UUID,
    period_id: UUID,
    period_update: FiscalPeriodUpdate,
    service: FiscalYearService = Depends(get_fiscal_year_service)
):
    updated = await service.update_period(period_id, period_update)
    return FiscalPeriodResponse.from_orm(updated)

@router.delete("/{fiscal_year_id}/periods/{period_id}", summary="Delete period")
async def delete_period(
    fiscal_year_id: UUID,
    period_id: UUID,
    service: FiscalYearService = Depends(get_fiscal_year_service)
):
    result = await service.delete_period(period_id)
    return result
