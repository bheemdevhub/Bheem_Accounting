# app/modules/accounting/api/v1/routes/profit_centers.py
"""Profit Center API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.accounting.core.schemas.accounting_schemas import ProfitCenterUpdate, ProfitCenterResponse
from app.modules.accounting.core.services.accounting_service import ProfitCenterService
from bheem_core.database import get_db

router = APIRouter(prefix="/profit-centers", tags=["Profit Centers"])

def get_profit_center_service(db: AsyncSession = Depends(get_db)):
    return ProfitCenterService(db)

@router.get("/{profit_center_id}", response_model=ProfitCenterResponse)
async def get_profit_center(profit_center_id: UUID, db: AsyncSession = Depends(get_db), service: ProfitCenterService = Depends(get_profit_center_service)):
    return ProfitCenterResponse(id=profit_center_id, company_id=UUID(int=0), name="", parent_profit_center_id=None, is_active=True, created_at=None, updated_at=None)

@router.put("/{profit_center_id}", response_model=ProfitCenterResponse)
async def update_profit_center(profit_center_id: UUID, profit_center: ProfitCenterUpdate, db: AsyncSession = Depends(get_db), service: ProfitCenterService = Depends(get_profit_center_service)):
    return ProfitCenterResponse(id=profit_center_id, company_id=UUID(int=0), name=profit_center.name or "", parent_profit_center_id=profit_center.parent_profit_center_id, is_active=profit_center.is_active if profit_center.is_active is not None else True, created_at=None, updated_at=None)

@router.delete("/{profit_center_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profit_center(profit_center_id: UUID, db: AsyncSession = Depends(get_db), service: ProfitCenterService = Depends(get_profit_center_service)):
    return None
