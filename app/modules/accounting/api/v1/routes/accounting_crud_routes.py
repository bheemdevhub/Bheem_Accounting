from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.accounting.core.services.accounting_service import CostCenterService
from app.modules.accounting.core.schemas.accounting_schemas import (
    CostCenterCreate, CostCenterUpdate, CostCenterResponse, CostCenterListResponse
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

# Create routers for accounts and cost centers
account_router = APIRouter(prefix="/accounts", tags=["Accounts"])
cost_center_router = APIRouter(prefix="/cost-centers", tags=["Cost Centers"])

@cost_center_router.post("/", response_model=CostCenterResponse, status_code=201, dependencies=[Depends(lambda: require_api_permission("costcenter.create"))])
async def create_cost_center(
    data: CostCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CostCenterService(db)
    cost_center = await service.create_cost_center(data)
    return CostCenterResponse.model_validate(cost_center)

@cost_center_router.get("/", response_model=CostCenterListResponse, dependencies=[Depends(lambda: require_api_permission("costcenter.read"))])
async def list_cost_centers(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CostCenterService(db)
    cost_centers = await service.list_cost_centers(skip=skip, limit=limit)
    return CostCenterListResponse(cost_centers=[CostCenterResponse.model_validate(c) for c in cost_centers], total=len(cost_centers))

@cost_center_router.get("/{cost_center_id}", response_model=CostCenterResponse, dependencies=[Depends(lambda: require_api_permission("costcenter.read"))])
async def get_cost_center(
    cost_center_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CostCenterService(db)
    cost_center = await service.get_cost_center(cost_center_id)
    return CostCenterResponse.model_validate(cost_center)

@cost_center_router.put("/{cost_center_id}", response_model=CostCenterResponse, dependencies=[Depends(lambda: require_api_permission("costcenter.update"))])
async def update_cost_center(
    cost_center_id: UUID,
    data: CostCenterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CostCenterService(db)
    cost_center = await service.update_cost_center(cost_center_id, data)
    return CostCenterResponse.model_validate(cost_center)

@cost_center_router.delete("/{cost_center_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(lambda: require_api_permission("costcenter.delete"))])
async def delete_cost_center(
    cost_center_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_roles([UserRole.ADMIN, UserRole.ACCOUNTANT]))
):
    service = CostCenterService(db)
    await service.delete_cost_center(cost_center_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
