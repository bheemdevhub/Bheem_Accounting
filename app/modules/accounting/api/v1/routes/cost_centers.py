# app/modules/accounting/api/v1/routes/cost_centers.py
"""Cost Center API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.accounting.core.schemas.accounting_schemas import CostCenterUpdate, CostCenterResponse
from app.modules.accounting.core.services.accounting_service import CostCenterService
from bheem_core.database import get_db

router = APIRouter(prefix="/cost-centers", tags=["Cost Centers"])

def get_cost_center_service(db: AsyncSession = Depends(get_db)):
    return CostCenterService(db)

@router.get("/{cost_center_id}", response_model=CostCenterResponse)
async def get_cost_center(cost_center_id: UUID, db: AsyncSession = Depends(get_db), service: CostCenterService = Depends(get_cost_center_service)):
    return CostCenterResponse(id=cost_center_id, company_id=UUID(int=0), name="", parent_cost_center_id=None, is_active=True, created_at=None, updated_at=None)

@router.put("/{cost_center_id}", response_model=CostCenterResponse)
async def update_cost_center(cost_center_id: UUID, cost_center: CostCenterUpdate, db: AsyncSession = Depends(get_db), service: CostCenterService = Depends(get_cost_center_service)):
    return CostCenterResponse(id=cost_center_id, company_id=UUID(int=0), name=cost_center.name or "", parent_cost_center_id=cost_center.parent_cost_center_id, is_active=cost_center.is_active if cost_center.is_active is not None else True, created_at=None, updated_at=None)

@router.delete("/{cost_center_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_center(cost_center_id: UUID, db: AsyncSession = Depends(get_db), service: CostCenterService = Depends(get_cost_center_service)):
    return None
