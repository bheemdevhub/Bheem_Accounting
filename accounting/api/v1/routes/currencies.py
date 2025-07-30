# app/modules/accounting/api/v1/routes/currencies.py
"""Currency and Exchange Rate API Routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from uuid import UUID
from typing import List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bheem_core.core.database import get_db
from bheem_core.modules.accounting.core.models.accounting_models import Currency
from bheem_core.modules.accounting.core.schemas.accounting_schemas import CurrencyCreate, CurrencyResponse
from bheem_core.modules.auth.core.services.permissions_service import require_roles, require_api_permission, get_current_user
from functools import partial

router = APIRouter(prefix="/currencies", tags=["Currencies"])

def permission_dep(permission_code: str):
    return Depends(partial(require_api_permission, permission_code=permission_code))

@router.get(
    "/",
    summary="List currencies",
    response_model=List[CurrencyResponse],
    dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), permission_dep("currency.list")]
)
async def list_currencies(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Currency))
    currencies = result.scalars().all()
    return [CurrencyResponse.model_validate(c) for c in currencies]

@router.post(
    "/",
    summary="Add currency",
    response_model=CurrencyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("Admin")), permission_dep("currency.create")]
)
async def add_currency(
    currency: CurrencyCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Currency).where(Currency.currency_code == currency.currency_code))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Currency code already exists.")
    new_currency = Currency(
        currency_code=currency.currency_code,
        currency_name=currency.currency_name,
        symbol=currency.symbol,
        decimal_places=currency.decimal_places,
        is_active=currency.is_active if currency.is_active is not None else True
    )
    db.add(new_currency)
    await db.commit()
    await db.refresh(new_currency)
    return CurrencyResponse.model_validate(new_currency)

@router.get(
    "/{currency_id}",
    summary="Get currency by ID",
    response_model=CurrencyResponse,
    dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), permission_dep("currency.view")]
)
async def get_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    currency = await db.get(Currency, currency_id)
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    return CurrencyResponse.model_validate(currency)

@router.put(
    "/{currency_id}",
    summary="Update currency",
    response_model=CurrencyResponse,
    dependencies=[Depends(require_roles("Admin")), permission_dep("currency.update")]
)
async def update_currency(
    currency_id: UUID,
    currency: CurrencyCreate,  # You may want a CurrencyUpdate schema
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    db_currency = await db.get(Currency, currency_id)
    if not db_currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    for field, value in currency.model_dump(exclude_unset=True).items():
        setattr(db_currency, field, value)
    await db.commit()
    await db.refresh(db_currency)
    return CurrencyResponse.model_validate(db_currency)

@router.delete(
    "/{currency_id}",
    summary="Delete currency",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("Admin")), permission_dep("currency.delete")]
)
async def delete_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    db_currency = await db.get(Currency, currency_id)
    if not db_currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    await db.delete(db_currency)
    await db.commit()
    return None

@router.get("/exchange-rates", summary="List exchange rates")
async def list_exchange_rates():
    pass

@router.post("/exchange-rates", summary="Add exchange rate")
async def add_exchange_rate():
    pass

