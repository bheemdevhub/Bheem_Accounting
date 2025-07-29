from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from typing import List, Optional
from uuid import UUID
from app.modules.accounting.core.schemas.accounting_schemas import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetListResponse,
    BudgetLineCreate, BudgetLineResponse,
    BudgetApprovalCreate, BudgetApprovalResponse,
    BudgetAllocationCreate, BudgetAllocationResponse,
    BudgetVarianceCreate, BudgetVarianceResponse,
    BudgetAuditLogCreate, BudgetAuditLogResponse,
    BudgetPeriodLineCreate, BudgetPeriodLineUpdate, BudgetPeriodLineResponse,
    BudgetAllocationLineCreate, BudgetAllocationLineUpdate, BudgetAllocationLineResponse, BudgetAllocationLineListResponse,
    BudgetTemplateCreate, BudgetTemplateUpdate, BudgetTemplateResponse, BudgetTemplateListResponse,
    BudgetVarianceListResponse, BudgetVarianceUpdate, BudgetAuditLogUpdate,BudgetAuditLogSummaryResponse
)
from app.modules.auth.core.services.permissions_service import require_roles, require_api_permission
from app.core.database import get_db
from sqlalchemy import select, or_, and_
from app.modules.accounting.core.models.accounting_models import Budget, BudgetLine, BudgetPeriodLine, BudgetApproval, BudgetAllocation, BudgetAllocationLine, BudgetTemplate, BudgetVariance, BudgetAuditLog
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.event_bus import EventBus
from app.modules.accounting.config import AccountingEventTypes
from app.modules.accounting.core.services.accounting_service import AccountingService

# Helper to get event bus instance

def get_event_bus(request: Request):
    return request.app.state.erp_system.event_bus if hasattr(request.app.state, 'erp_system') else None

router = APIRouter(prefix="/budgets", tags=["Budgets"])

# --- Budget Endpoints ---
@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def create_budget(budget: BudgetCreate, db: AsyncSession = Depends(get_db)):
    # Check for duplicate budget code for the same company and fiscal year
    stmt = select(Budget).where(
        Budget.budget_code == getattr(budget, "budget_code", None),
        Budget.company_id == budget.company_id,
        Budget.fiscal_year_id == budget.fiscal_year_id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Budget code already exists for this company and fiscal year.")
    # Create Budget instance
    new_budget = Budget(
        budget_name=budget.budget_name,  # Use correct schema attribute
        budget_code=getattr(budget, "budget_code", None),
        budget_type=getattr(budget, "budget_type", None),
        company_id=budget.company_id,
        fiscal_year_id=budget.fiscal_year_id,
        budget_version=getattr(budget, "budget_version", None),
        version_type=getattr(budget, "version_type", None),
        parent_budget_id=getattr(budget, "parent_budget_id", None),
        status=getattr(budget, "status", None),
        submitted_by=getattr(budget, "submitted_by", None),
        submitted_date=getattr(budget, "submitted_date", None),
        approved_by=getattr(budget, "approved_by", None),
        approved_date=getattr(budget, "approved_date", None),
        start_date=getattr(budget, "start_date", None),
        end_date=getattr(budget, "end_date", None),
        budget_currency_id=getattr(budget, "budget_currency_id", None),
        allow_line_item_changes=getattr(budget, "allow_line_item_changes", None),
        auto_allocate_periods=getattr(budget, "auto_allocate_periods", None),
        allocation_method=getattr(budget, "allocation_method", None),
        description=getattr(budget, "description", None),
        assumptions=getattr(budget, "assumptions", None),
        notes=getattr(budget, "notes", None),
        tags=getattr(budget, "tags", None),
        created_by=getattr(budget, "created_by", None),
        updated_by=getattr(budget, "updated_by", None)
    )
    db.add(new_budget)
    await db.commit()
    await db.refresh(new_budget)
    return BudgetResponse.model_validate(new_budget, from_attributes=True)

@router.get("/", response_model=BudgetListResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def list_budgets(
    db: AsyncSession = Depends(get_db),
    company_id: UUID = Query(None),
    fiscal_year_id: UUID = Query(None),
    budget_type: str = Query(None),
    status: str = Query(None),
    search: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    stmt = select(Budget)
    if company_id:
        stmt = stmt.where(Budget.company_id == company_id)
    if fiscal_year_id:
        stmt = stmt.where(Budget.fiscal_year_id == fiscal_year_id)
    if budget_type:
        stmt = stmt.where(Budget.budget_type == budget_type)
    if status:
        stmt = stmt.where(Budget.status == status)
    if search:
        stmt = stmt.where(Budget.budget_name.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    budgets = result.scalars().all()
    return BudgetListResponse(budgets=[BudgetResponse.model_validate(b, from_attributes=True) for b in budgets])

@router.get("/{budget_id}", response_model=BudgetResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def get_budget(budget_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return BudgetResponse.model_validate(budget, from_attributes=True)

@router.put("/{budget_id}", response_model=BudgetResponse, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def update_budget(budget_id: UUID, budget_update: BudgetUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    for field, value in budget_update.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return BudgetResponse.model_validate(budget, from_attributes=True)

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin"))])
async def delete_budget(budget_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.delete(budget)
    await db.commit()
    return None

# --- Budget Line Endpoints ---
@router.post("/{budget_id}/lines", response_model=BudgetLineResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin")), Depends(lambda: require_api_permission("budgetline.create"))])
async def create_budget_line(
    budget_id: UUID,
    line: BudgetLineCreate,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    # Check if budget exists
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    # Remove budget_id from line if present
    line_data = line.model_dump()
    line_data.pop("budget_id", None)
    new_line = BudgetLine(**line_data, budget_id=budget_id)
    db.add(new_line)
    await db.commit()
    await db.refresh(new_line)
    # Trigger event bus if available
    if hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetline.created", {"budget_line_id": str(new_line.id)})
    return BudgetLineResponse.model_validate(new_line, from_attributes=True)

@router.get("/{budget_id}/lines", response_model=List[BudgetLineResponse], dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetline.list"))])
async def list_budget_lines(
    budget_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None, description="Search in description or notes"),
    db: AsyncSession = Depends(get_db)
):
    query = select(BudgetLine).where(BudgetLine.budget_id == budget_id)
    if search:
        query = query.where(or_(BudgetLine.description.ilike(f"%{search}%"), BudgetLine.notes.ilike(f"%{search}%")))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    lines = result.scalars().all()
    return [BudgetLineResponse.model_validate(l, from_attributes=True) for l in lines]

@router.get("/{budget_id}/lines/{line_id}", response_model=BudgetLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetline.view"))])
async def get_budget_line(budget_id: UUID, line_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BudgetLine).where(and_(BudgetLine.budget_id == budget_id, BudgetLine.id == line_id)))
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Budget line not found")
    return BudgetLineResponse.model_validate(line, from_attributes=True)

@router.put("/{budget_id}/lines/{line_id}", response_model=BudgetLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def update_budget_line(budget_id: UUID, line_id: UUID, line: BudgetLineCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetLine).where(and_(BudgetLine.budget_id == budget_id, BudgetLine.id == line_id)))
    db_line = result.scalar_one_or_none()
    if not db_line:
        raise HTTPException(status_code=404, detail="Budget line not found")
    line_data = line.model_dump()
    line_data.pop("budget_id", None)
    for k, v in line_data.items():
        setattr(db_line, k, v)
    await db.commit()
    await db.refresh(db_line)
    if hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetline.updated", {"budget_line_id": str(db_line.id)})
    return BudgetLineResponse.model_validate(db_line, from_attributes=True)

@router.delete("/{budget_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), Depends(lambda: require_api_permission("budgetline.delete"))])
async def delete_budget_line(budget_id: UUID, line_id: UUID, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetLine).where(and_(BudgetLine.budget_id == budget_id, BudgetLine.id == line_id)))
    db_line = result.scalar_one_or_none()
    if not db_line:
        raise HTTPException(status_code=404, detail="Budget line not found")
    await db.delete(db_line)
    await db.commit()
    if hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetline.deleted", {"budget_line_id": str(line_id)})
    return None

# --- Budget Approval Endpoints ---
@router.post("/{budget_id}/approvals", response_model=BudgetApprovalResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Admin")), Depends(lambda: require_api_permission("budgetapproval.create"))])
async def create_budget_approval(budget_id: UUID, approval: BudgetApprovalCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    approval_data = approval.model_dump()
    # Accept both 'approval_status' and 'status' for compatibility
    approval_status = approval_data.get("approval_status") or approval_data.get("status")
    if not approval_status:
        raise HTTPException(status_code=400, detail="approval_status is required.")
    # Remove 'status' if present to avoid passing to model
    approval_data.pop("status", None)
    # Compose model fields for BudgetApproval
    model_fields = dict(
        budget_id=budget_id,
        approval_level=approval_data["approval_level"],
        approver_id=approval_data["approver_id"],
        approver_name=approval_data["approver_name"],
        approver_role=approval_data.get("approver_role"),
        approval_status=approval_status,
        approval_date=approval_data.get("approval_date"),
        comments=approval_data.get("comments"),
        created_by=approval_data.get("created_by"),
        updated_by=approval_data.get("updated_by"),
        is_active=approval_data.get("is_active", True)
    )
    new_approval = BudgetApproval(**model_fields)
    db.add(new_approval)
    await db.commit()
    await db.refresh(new_approval)
    # Trigger event bus if available
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetapproval.created", {"budget_approval_id": str(new_approval.id)})
    return BudgetApprovalResponse.model_validate(new_approval, from_attributes=True)

@router.get("/{budget_id}/approvals", response_model=List[BudgetApprovalResponse], dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetapproval.list"))])
async def list_budget_approvals(
    budget_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None),
    approver_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(BudgetApproval).where(BudgetApproval.budget_id == budget_id)
    if approval_status:
        stmt = stmt.where(BudgetApproval.approval_status == approval_status)
    if approver_name:
        stmt = stmt.where(BudgetApproval.approver_name.ilike(f"%{approver_name}%"))
    if search:
        stmt = stmt.where(or_(BudgetApproval.comments.ilike(f"%{search}%"), BudgetApproval.approver_name.ilike(f"%{search}%")))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    approvals = result.scalars().all()
    return [BudgetApprovalResponse.model_validate(a, from_attributes=True) for a in approvals]

@router.get("/{budget_id}/approvals/{approval_id}", response_model=BudgetApprovalResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetapproval.get"))])
async def get_budget_approval(budget_id: UUID, approval_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BudgetApproval).where(BudgetApproval.budget_id == budget_id, BudgetApproval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Budget approval not found")
    return BudgetApprovalResponse.model_validate(approval, from_attributes=True)

@router.put("/{budget_id}/approvals/{approval_id}", response_model=BudgetApprovalResponse, dependencies=[Depends(require_roles("Admin")), Depends(lambda: require_api_permission("budgetapproval.update"))])
async def update_budget_approval(budget_id: UUID, approval_id: UUID, approval_update: BudgetApprovalCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetApproval).where(BudgetApproval.budget_id == budget_id, BudgetApproval.id == approval_id))
    db_approval = result.scalar_one_or_none()
    if not db_approval:
        raise HTTPException(status_code=404, detail="Budget approval not found")
    update_data = approval_update.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_approval, k, v)
    await db.commit()
    await db.refresh(db_approval)
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetapproval.updated", {"budget_approval_id": str(db_approval.id)})
    return BudgetApprovalResponse.model_validate(db_approval, from_attributes=True)

@router.delete("/{budget_id}/approvals/{approval_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), Depends(lambda: require_api_permission("budgetapproval.delete"))])
async def delete_budget_approval(budget_id: UUID, approval_id: UUID, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetApproval).where(BudgetApproval.budget_id == budget_id, BudgetApproval.id == approval_id))
    db_approval = result.scalar_one_or_none()
    if not db_approval:
        raise HTTPException(status_code=404, detail="Budget approval not found")
    await db.delete(db_approval)
    await db.commit()
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetapproval.deleted", {"budget_approval_id": str(approval_id)})
    return None

# --- Budget Allocation Endpoints ---
@router.post("/{budget_id}/allocations", response_model=BudgetAllocationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin")), Depends(lambda: require_api_permission("budgetallocation.create"))])
async def create_budget_allocation(
    budget_id: UUID,
    allocation: BudgetAllocationCreate,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    # Check if budget exists
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail=f"Budget not found for id: {budget_id}. Please create the budget first or verify the budget_id.")
    # Check if source_budget_line_id exists
    line_result = await db.execute(select(BudgetLine).where(BudgetLine.id == allocation.source_budget_line_id))
    source_line = line_result.scalar_one_or_none()
    if not source_line:
        raise HTTPException(status_code=400, detail=f"Source budget line does not exist for id: {allocation.source_budget_line_id}. Please create the budget line first or verify the source_budget_line_id.")
    # Remove budget_id from allocation if present
    alloc_data = allocation.model_dump()
    alloc_data.pop("budget_id", None)
    new_alloc = BudgetAllocation(**alloc_data, budget_id=budget_id)
    db.add(new_alloc)
    await db.commit()
    await db.refresh(new_alloc)
    # Trigger event bus if available
    if hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetallocation.created", {"budget_allocation_id": str(new_alloc.id)})
    return BudgetAllocationResponse.model_validate(new_alloc, from_attributes=True)

@router.get("/{budget_id}/allocations", response_model=List[BudgetAllocationResponse], dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetallocation.list"))])
async def list_budget_allocations(budget_id: UUID, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    stmt = select(BudgetAllocation).where(BudgetAllocation.budget_id == budget_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    allocations = result.scalars().all()
    return [BudgetAllocationResponse.model_validate(a, from_attributes=True) for a in allocations]

@router.get("/{budget_id}/allocations/{allocation_id}", response_model=BudgetAllocationResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetallocation.get"))])
async def get_budget_allocation(budget_id: UUID, allocation_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BudgetAllocation).where(BudgetAllocation.budget_id == budget_id, BudgetAllocation.id == allocation_id))
    allocation = result.scalar_one_or_none()
    if not allocation:
        raise HTTPException(status_code=404, detail="Budget allocation not found")
    return BudgetAllocationResponse.model_validate(allocation, from_attributes=True)

@router.put("/{budget_id}/allocations/{allocation_id}", response_model=BudgetAllocationResponse, dependencies=[Depends(require_roles("Accountant", "Admin")), Depends(lambda: require_api_permission("budgetallocation.update"))])
async def update_budget_allocation(budget_id: UUID, allocation_id: UUID, allocation_update: BudgetAllocationCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetAllocation).where(BudgetAllocation.budget_id == budget_id, BudgetAllocation.id == allocation_id))
    db_allocation = result.scalar_one_or_none()
    if not db_allocation:
        raise HTTPException(status_code=404, detail="Budget allocation not found")
    update_data = allocation_update.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_allocation, k, v)
    await db.commit()
    await db.refresh(db_allocation)
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetallocation.updated", {"budget_allocation_id": str(db_allocation.id)})
    return BudgetAllocationResponse.model_validate(db_allocation, from_attributes=True)

@router.delete("/{budget_id}/allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), Depends(lambda: require_api_permission("budgetallocation.delete"))])
async def delete_budget_allocation(budget_id: UUID, allocation_id: UUID, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetAllocation).where(BudgetAllocation.budget_id == budget_id, BudgetAllocation.id == allocation_id))
    db_allocation = result.scalar_one_or_none()
    if not db_allocation:
        raise HTTPException(status_code=404, detail="Budget allocation not found")
    await db.delete(db_allocation)
    await db.commit()
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetallocation.deleted", {"budget_allocation_id": str(allocation_id)})
    return None

# --- Budget Variance Endpoints ---
@router.post("/{budget_id}/variances", response_model=BudgetVarianceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def create_budget_variance(
    budget_id: UUID,
    variance: BudgetVarianceCreate,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    # Validate budget_line_id exists and belongs to the budget
    budget_line_result = await db.execute(
        select(BudgetLine).where(
            BudgetLine.id == variance.budget_line_id,
            BudgetLine.budget_id == budget_id
        )
    )
    budget_line = budget_line_result.scalar_one_or_none()
    if not budget_line:
        raise HTTPException(
            status_code=404, 
            detail="Budget line not found or doesn't belong to this budget"
        )
    
    # Create the budget variance directly
    new_variance = BudgetVariance(**variance.model_dump())
    db.add(new_variance)
    await db.commit()
    await db.refresh(new_variance)
    
    # Trigger event bus if available
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish(
            "accounting.budgetvariance.created", 
            {"budget_variance_id": str(new_variance.id)}
        )
    
    return BudgetVarianceResponse.model_validate(new_variance, from_attributes=True)

@router.get("/{budget_id}/variances", response_model=List[BudgetVarianceResponse], dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def list_budget_variances(budget_id: UUID, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), db: AsyncSession = Depends(get_db)):
    stmt = select(BudgetVariance).join(BudgetLine).where(BudgetLine.budget_id == budget_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    variances = result.scalars().all()
    return [BudgetVarianceResponse.model_validate(v) for v in variances]

@router.get("/{budget_id}/variances/{variance_id}", response_model=BudgetVarianceResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def get_budget_variance(budget_id: UUID, variance_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(BudgetVariance).join(BudgetLine).where(BudgetVariance.id == variance_id, BudgetLine.budget_id == budget_id)
    result = await db.execute(stmt)
    variance = result.scalar_one_or_none()
    if not variance:
        raise HTTPException(status_code=404, detail="Budget variance not found")
    return BudgetVarianceResponse.model_validate(variance)

@router.put("/{budget_id}/variances/{variance_id}", response_model=BudgetVarianceResponse, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def update_budget_variance(budget_id: UUID, variance_id: UUID, update: BudgetVarianceUpdate, db: AsyncSession = Depends(get_db), request: Request = None):
    service = AccountingService(db, get_event_bus(request))
    # Ensure variance belongs to budget
    stmt = select(BudgetVariance).join(BudgetLine).where(BudgetVariance.id == variance_id, BudgetLine.budget_id == budget_id)
    result = await db.execute(stmt)
    variance = result.scalar_one_or_none()
    if not variance:
        raise HTTPException(status_code=404, detail="Budget variance not found")
    updated = await service.update_budget_variance(variance_id, update)
    return BudgetVarianceResponse.model_validate(updated)

@router.delete("/{budget_id}/variances/{variance_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin"))])
async def delete_budget_variance(budget_id: UUID, variance_id: UUID, db: AsyncSession = Depends(get_db), request: Request = None):
    service = AccountingService(db, get_event_bus(request))
    # Ensure variance belongs to budget
    stmt = select(BudgetVariance).join(BudgetLine).where(BudgetVariance.id == variance_id, BudgetLine.budget_id == budget_id)
    result = await db.execute(stmt)
    variance = result.scalar_one_or_none()
    if not variance:
        raise HTTPException(status_code=404, detail="Budget variance not found")
    await service.delete_budget_variance(variance_id)
    return None

# --- Budget Audit Log Endpoints ---
@router.post("/{budget_id}/audit-logs", response_model=BudgetAuditLogResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Admin"))])
async def create_budget_audit_log(
    budget_id: UUID,
    log: BudgetAuditLogCreate,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Create a new budget audit log entry"""
    service = AccountingService(db, get_event_bus(request))
    new_log = await service.create_budget_audit_log(log, budget_id)
    return BudgetAuditLogResponse.model_validate(new_log, from_attributes=True)

@router.get("/{budget_id}/audit-logs", response_model=List[BudgetAuditLogResponse], dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def list_budget_audit_logs(
    budget_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action: str = Query(None),
    performed_by: UUID = Query(None),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """List all audit logs for a budget"""
    service = AccountingService(db, get_event_bus(request))
    logs = await service.list_budget_audit_logs(
        budget_id=budget_id,
        skip=skip,
        limit=limit,
        action=action,
        performed_by=performed_by
    )
    return [BudgetAuditLogResponse.model_validate(log, from_attributes=True) for log in logs]

@router.get("/{budget_id}/audit-logs/{log_id}", response_model=BudgetAuditLogResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def get_budget_audit_log(
    budget_id: UUID,
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Get a specific audit log entry"""
    service = AccountingService(db, get_event_bus(request))
    
    # Get the log and verify it belongs to the budget
    log = await service.get_budget_audit_log(log_id)
    if log.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Budget audit log not found")
    
    return BudgetAuditLogResponse.model_validate(log, from_attributes=True)

@router.put("/{budget_id}/audit-logs/{log_id}", response_model=BudgetAuditLogResponse, dependencies=[Depends(require_roles("Admin"))])
async def update_budget_audit_log(
    budget_id: UUID,
    log_id: UUID,
    log_update: BudgetAuditLogUpdate,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Update a budget audit log entry"""
    service = AccountingService(db, get_event_bus(request))
    
    # Verify the log belongs to the budget
    existing_log = await service.get_budget_audit_log(log_id)
    if existing_log.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Budget audit log not found")
    
    updated_log = await service.update_budget_audit_log(log_id, log_update)
    return BudgetAuditLogResponse.model_validate(updated_log, from_attributes=True)

@router.delete("/{budget_id}/audit-logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin"))])
async def delete_budget_audit_log(
    budget_id: UUID,
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Delete a budget audit log entry"""
    service = AccountingService(db, get_event_bus(request))
    
    # Verify the log belongs to the budget
    existing_log = await service.get_budget_audit_log(log_id)
    if existing_log.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Budget audit log not found")
    
    await service.delete_budget_audit_log(log_id)
    return None

@router.get("/{budget_id}/audit-logs/summary", response_model=BudgetAuditLogSummaryResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def get_budget_audit_summary(
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Get audit summary for a budget"""
    service = AccountingService(db, get_event_bus(request))
    summary = await service.get_budget_audit_summary(budget_id)
    return summary

# --- Budget Period Line Endpoints ---
@router.post("/{budget_id}/lines/{line_id}/period-lines", response_model=BudgetPeriodLineResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin")), Depends(lambda: require_api_permission("budgetperiodline.create"))])
async def create_budget_period_line(
    budget_id: UUID,
    line_id: UUID,
    period_line: BudgetPeriodLineCreate,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    # Accept payload without budget_line_id, set it from path param
    period_line_data = period_line.model_dump(exclude={"budget_line_id"})
    period_line_data["budget_line_id"] = line_id
    new_period_line = BudgetPeriodLine(**period_line_data)
    db.add(new_period_line)
    await db.commit()
    await db.refresh(new_period_line)
    # Event bus: publish event
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetperiodline.created", {"budget_period_line_id": str(new_period_line.id)})
    return BudgetPeriodLineResponse.model_validate(new_period_line, from_attributes=True)

@router.get("/{budget_id}/lines/{line_id}/period-lines", response_model=List[BudgetPeriodLineResponse], dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetperiodline.list"))])
async def list_budget_period_lines(budget_id: UUID, line_id: UUID, search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    stmt = select(BudgetPeriodLine).where(BudgetPeriodLine.budget_line_id == line_id)
    if search:
        stmt = stmt.where(or_(BudgetPeriodLine.notes.ilike(f"%{search}%"), BudgetPeriodLine.budget_amount == search))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    period_lines = result.scalars().all()
    return [BudgetPeriodLineResponse.model_validate(pl, from_attributes=True) for pl in period_lines]

@router.get("/{budget_id}/lines/{line_id}/period-lines/{period_line_id}", response_model=BudgetPeriodLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetperiodline.get"))])
async def get_budget_period_line(budget_id: UUID, line_id: UUID, period_line_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BudgetPeriodLine).where(BudgetPeriodLine.budget_line_id == line_id, BudgetPeriodLine.id == period_line_id))
    period_line = result.scalar_one_or_none()
    if not period_line:
        raise HTTPException(status_code=404, detail="Budget period line not found")
    return BudgetPeriodLineResponse.model_validate(period_line, from_attributes=True)

@router.put("/{budget_id}/lines/{line_id}/period-lines/{period_line_id}", response_model=BudgetPeriodLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin")), Depends(lambda: require_api_permission("budgetperiodline.update"))])
async def update_budget_period_line(budget_id: UUID, line_id: UUID, period_line_id: UUID, period_line: BudgetPeriodLineUpdate, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetPeriodLine).where(BudgetPeriodLine.budget_line_id == line_id, BudgetPeriodLine.id == period_line_id))
    db_period_line = result.scalar_one_or_none()
    if not db_period_line:
        raise HTTPException(status_code=404, detail="Budget period line not found")
    update_data = period_line.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_period_line, k, v)
    await db.commit()
    await db.refresh(db_period_line)
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetperiodline.updated", {"budget_period_line_id": str(db_period_line.id)})
    return BudgetPeriodLineResponse.model_validate(db_period_line, from_attributes=True)

@router.delete("/{budget_id}/lines/{line_id}/period-lines/{period_line_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), Depends(lambda: require_api_permission("budgetperiodline.delete"))])
async def delete_budget_period_line(budget_id: UUID, line_id: UUID, period_line_id: UUID, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetPeriodLine).where(BudgetPeriodLine.budget_line_id == line_id, BudgetPeriodLine.id == period_line_id))
    db_period_line = result.scalar_one_or_none()
    if not db_period_line:
        raise HTTPException(status_code=404, detail="Budget period line not found")
    await db.delete(db_period_line)
    await db.commit()
    if request and hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetperiodline.deleted", {"budget_period_line_id": str(period_line_id)})
    return None

# --- Budget Allocation Line Endpoints ---
@router.post("/{budget_id}/allocations/{allocation_id}/lines", response_model=BudgetAllocationLineResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin")), Depends(lambda: require_api_permission("budgetallocationline.create"))])
async def create_budget_allocation_line(budget_id: UUID, allocation_id: UUID, line: BudgetAllocationLineCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    # Check allocation exists
    alloc_result = await db.execute(select(BudgetAllocation).where(BudgetAllocation.id == allocation_id, BudgetAllocation.budget_id == budget_id))
    allocation = alloc_result.scalar_one_or_none()
    if not allocation:
        raise HTTPException(status_code=404, detail="Budget allocation not found")
    # Check target budget line exists
    target_result = await db.execute(select(BudgetLine).where(BudgetLine.id == line.target_budget_line_id))
    target_line = target_result.scalar_one_or_none()
    if not target_line:
        raise HTTPException(status_code=400, detail=f"Target budget line does not exist for id: {line.target_budget_line_id}")
    line_data = line.model_dump()
    line_data.pop("allocation_id", None)  # Remove if present
    new_line = BudgetAllocationLine(**line_data, allocation_id=allocation_id)
    db.add(new_line)
    await db.commit()
    await db.refresh(new_line)
    # Event bus trigger
    if hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetallocationline.created", {"budget_allocation_line_id": str(new_line.id)})
    return BudgetAllocationLineResponse.model_validate(new_line, from_attributes=True)

@router.get("/{budget_id}/allocations/{allocation_id}/lines", response_model=BudgetAllocationLineListResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetallocationline.list"))])
async def list_budget_allocation_lines(budget_id: UUID, allocation_id: UUID, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), db: AsyncSession = Depends(get_db)):
    stmt = select(BudgetAllocationLine).where(BudgetAllocationLine.allocation_id == allocation_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    lines = result.scalars().all()
    return BudgetAllocationLineListResponse(allocation_lines=[BudgetAllocationLineResponse.model_validate(l, from_attributes=True) for l in lines], total=len(lines))

@router.get("/{budget_id}/allocations/{allocation_id}/lines/{line_id}", response_model=BudgetAllocationLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), Depends(lambda: require_api_permission("budgetallocationline.get"))])
async def get_budget_allocation_line(budget_id: UUID, allocation_id: UUID, line_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BudgetAllocationLine).where(BudgetAllocationLine.id == line_id, BudgetAllocationLine.allocation_id == allocation_id))
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Budget allocation line not found")
    return BudgetAllocationLineResponse.model_validate(line, from_attributes=True)

@router.put("/{budget_id}/allocations/{allocation_id}/lines/{line_id}", response_model=BudgetAllocationLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin")), Depends(lambda: require_api_permission("budgetallocationline.update"))])
async def update_budget_allocation_line(budget_id: UUID, allocation_id: UUID, line_id: UUID, line_update: BudgetAllocationLineUpdate, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetAllocationLine).where(BudgetAllocationLine.id == line_id, BudgetAllocationLine.allocation_id == allocation_id))
    db_line = result.scalar_one_or_none()
    if not db_line:
        raise HTTPException(status_code=404, detail="Budget allocation line not found")
    for k, v in line_update.model_dump(exclude_unset=True).items():
        setattr(db_line, k, v)
    db.add(db_line)
    await db.commit()
    await db.refresh(db_line)
    if hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetallocationline.updated", {"budget_allocation_line_id": str(db_line.id)})
    return BudgetAllocationLineResponse.model_validate(db_line, from_attributes=True)

@router.delete("/{budget_id}/allocations/{allocation_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), Depends(lambda: require_api_permission("budgetallocationline.delete"))])
async def delete_budget_allocation_line(budget_id: UUID, allocation_id: UUID, line_id: UUID, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(BudgetAllocationLine).where(BudgetAllocationLine.id == line_id, BudgetAllocationLine.allocation_id == allocation_id))
    db_line = result.scalar_one_or_none()
    if not db_line:
        raise HTTPException(status_code=404, detail="Budget allocation line not found")
    await db.delete(db_line)
    await db.commit()
    if hasattr(request.app.state, "event_bus"):
        await request.app.state.event_bus.publish("accounting.budgetallocationline.deleted", {"budget_allocation_line_id": str(line_id)})
    return None

# --- Budget Template Endpoints ---
@router.post("/templates", response_model=BudgetTemplateResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def create_budget_template(template: BudgetTemplateCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    event_bus = get_event_bus(request) if request else None
    service = AccountingService(db, event_bus)
    try:
        new_template = await service.create_budget_template(template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if event_bus:
        await event_bus.publish("accounting.budgettemplate.created", {"budget_template_id": str(new_template.id)})
    return BudgetTemplateResponse.model_validate(new_template, from_attributes=True)

@router.get("/templates/{template_id}", response_model=BudgetTemplateResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def get_budget_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    service = AccountingService(db)
    try:
        template = await service.get_budget_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return BudgetTemplateResponse.model_validate(template, from_attributes=True)

@router.get("/companies/{company_id}/templates", response_model=BudgetTemplateListResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer"))])
async def list_budget_templates(company_id: UUID, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    service = AccountingService(db)
    templates = await service.list_budget_templates(company_id, skip, limit)
    return BudgetTemplateListResponse(templates=[BudgetTemplateResponse.model_validate(t, from_attributes=True) for t in templates], total=len(templates))

@router.put("/templates/{template_id}", response_model=BudgetTemplateResponse, dependencies=[Depends(require_roles("Accountant", "Admin"))])
async def update_budget_template(template_id: UUID, update: BudgetTemplateUpdate, db: AsyncSession = Depends(get_db), request: Request = None):
    event_bus = get_event_bus(request) if request else None
    service = AccountingService(db, event_bus)
    try:
        updated = await service.update_budget_template(template_id, update)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if event_bus:
        await event_bus.publish("accounting.budgettemplate.updated", {"budget_template_id": str(updated.id)})
    return BudgetTemplateResponse.model_validate(updated, from_attributes=True)

@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin"))])
async def delete_budget_template(template_id: UUID, db: AsyncSession = Depends(get_db), request: Request = None):
    event_bus = get_event_bus(request) if request else None
    service = AccountingService(db, event_bus)
    try:
        await service.delete_budget_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if event_bus:
        await event_bus.publish("accounting.budgettemplate.deleted", {"budget_template_id": str(template_id)})
    return None
