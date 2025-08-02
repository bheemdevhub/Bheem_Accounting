# app/modules/accounting/api/v1/routes/budgets.py
"""Budgets API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.accounting.core.schemas.accounting_schemas import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetListResponse
from app.modules.accounting.core.services.accounting_service import AccountingService
from bheem_core.database import get_db

router = APIRouter(prefix="/budgets", tags=["Budgets"])

def get_accounting_service(db: AsyncSession = Depends(get_db)):
    return AccountingService(db)

@router.get("/", response_model=BudgetListResponse, summary="List budgets for a company")
async def list_budgets(db: AsyncSession = Depends(get_db), service: AccountingService = Depends(get_accounting_service)):
    return BudgetListResponse(budgets=[])

@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED, summary="Create budget")
async def create_budget(budget: BudgetCreate, db: AsyncSession = Depends(get_db), service: AccountingService = Depends(get_accounting_service)):
    return BudgetResponse(id=UUID(int=0), company_id=budget.company_id, name=budget.name, fiscal_year_id=budget.fiscal_year_id, status=budget.status, total_amount=budget.total_amount, created_at=None, updated_at=None)

@router.get("/{budget_id}", response_model=BudgetResponse, summary="Get budget details")
async def get_budget(budget_id: UUID, db: AsyncSession = Depends(get_db), service: AccountingService = Depends(get_accounting_service)):
    return BudgetResponse(id=budget_id, company_id=UUID(int=0), name="", fiscal_year_id=UUID(int=0), status=None, total_amount=None, created_at=None, updated_at=None)

@router.put("/{budget_id}", response_model=BudgetResponse, summary="Update budget")
async def update_budget(budget_id: UUID, budget: BudgetUpdate, db: AsyncSession = Depends(get_db), service: AccountingService = Depends(get_accounting_service)):
    return BudgetResponse(id=budget_id, company_id=UUID(int=0), name=budget.name or "", fiscal_year_id=UUID(int=0), status=budget.status, total_amount=budget.total_amount, created_at=None, updated_at=None)

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete budget")
async def delete_budget(budget_id: UUID, db: AsyncSession = Depends(get_db), service: AccountingService = Depends(get_accounting_service)):
    return None

@router.get("/{budget_id}/lines", summary="List budget lines")
async def list_budget_lines(budget_id: UUID):
    pass

@router.post("/{budget_id}/lines", summary="Add budget line")
async def add_budget_line(budget_id: UUID):
    pass

@router.get("/{budget_id}/approvals", summary="List approvals")
async def list_approvals(budget_id: UUID):
    pass

@router.post("/{budget_id}/approvals", summary="Add approval")
async def add_approval(budget_id: UUID):
    pass

@router.get("/{budget_id}/allocations", summary="List allocations")
async def list_allocations(budget_id: UUID):
    pass

@router.post("/{budget_id}/allocations", summary="Add allocation")
async def add_allocation(budget_id: UUID):
    pass

@router.get("/{budget_id}/variances", summary="List variances")
async def list_variances(budget_id: UUID):
    pass

@router.get("/{budget_id}/audit-logs", summary="List audit logs")
async def list_audit_logs(budget_id: UUID):
    pass
