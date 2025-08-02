# app/modules/accounting/api/v1/routes/accounts.py
"""Unified accounting API routes for all major entities"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.accounting.core.services.accounting_service import AccountingService
from app.modules.accounting.core.schemas.accounting_schemas import (
    AccountCreate, AccountUpdate, AccountResponse, AccountListResponse
)
from app.core.event_bus import EventBus
from app.modules.auth.core.services.permissions_service import require_roles, require_api_permission
from app.core.database import get_db

router = APIRouter(tags=["Accounts"])

def get_event_bus():
    # Replace with actual event bus instance
    return EventBus()

# -------------------
# Account Endpoints
# -------------------
@router.get("/", response_model=AccountListResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def list_accounts(
    search: Optional[str] = Query(None, description="Search by account code or name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    service = AccountingService(db)
    return await service.list_accounts(search=search, skip=skip, limit=limit)

@router.post("/", response_model=AccountResponse, status_code=201, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def create_account(account: AccountCreate, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    service = AccountingService(db, event_bus)
    return await service.create_account(account)

@router.get("/{account_id}", response_model=AccountResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    service = AccountingService(db)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.put("/{account_id}", response_model=AccountResponse, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def update_account(account_id: UUID, account: AccountUpdate, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    service = AccountingService(db, event_bus)
    updated = await service.update_account(account_id, account)
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found")
    return updated

@router.delete("/{account_id}", response_model=dict, status_code=200, dependencies=[Depends(require_roles("Admin"))])
async def delete_account(account_id: UUID, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    service = AccountingService(db, event_bus)
    deleted = await service.delete_account(account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"detail": "Account deleted successfully"}

# Only account endpoints remain in this file. Cost center and other endpoints should be in their respective files.

