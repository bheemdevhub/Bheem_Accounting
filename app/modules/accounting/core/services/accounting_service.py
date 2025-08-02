from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from typing import List, Optional
from uuid import UUID

# Try to import from bheem_core, fallback to local stubs if not available
try:
    from bheem_core.event_bus import EventBus
except ImportError:
    from app.core.bheem_core_stubs import EventBus
from app.modules.accounting.core.models.accounting_models import LedgerAccount as Account, CostCenter, FiscalYear, FiscalPeriod, BudgetTemplate, BudgetVariance
# If BudgetAuditLog is needed, import from its actual location:
# from app.modules.accounting.core.models.accounting_models import BudgetAuditLog
from app.modules.accounting.core.schemas.accounting_schemas import (
    AccountCreate, AccountUpdate,
    CostCenterCreate, CostCenterUpdate,
    FiscalYearCreate, FiscalYearUpdate,
    FiscalPeriodCreate, FiscalPeriodUpdate,
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse,
    ProfitCenterCreate, ProfitCenterUpdate, ProfitCenterResponse, ProfitCenterListResponse,
    # Add missing journal entry schemas:
    JournalEntryBase, JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse, JournalEntryListResponse,
    JournalEntryLineCreate, JournalEntryLineResponse,
    # Add missing budget schemas:
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetListResponse,
    BudgetLineCreate, BudgetLineResponse,
    BudgetApprovalCreate, BudgetApprovalResponse,
    BudgetAllocationCreate, BudgetAllocationResponse,
    BudgetVarianceCreate, BudgetVarianceResponse,
    BudgetAuditLogCreate, BudgetAuditLogResponse,
    AccountResponse,
    BudgetAllocationLineCreate, BudgetAllocationLineUpdate, BudgetAllocationLineResponse, BudgetAllocationLineListResponse,
    BudgetTemplateCreate, BudgetTemplateUpdate, BudgetTemplateResponse, BudgetTemplateListResponse,
    BudgetVarianceUpdate, BudgetAuditLogUpdate
)

# Try to import from bheem_core, fallback to local stubs if not available
try:
    from bheem_core.shared.models import Company, Currency
except ImportError:
    from app.core.bheem_core_stubs import Company, Currency
from sqlalchemy import select, or_, func
from app.modules.accounting.core.schemas.account_response import AccountResponse
from app.modules.accounting.config import AccountingEventTypes

# Dummy event bus instance (replace with real one in app context)
event_bus = EventBus()

class AccountingService:
    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus

    async def create_account(self, data: AccountCreate):
        stmt = select(Account).where(Account.account_code == data.account_code, Account.company_id == data.company_id)
        result = await self.db.execute(stmt)
        if result.scalar():
            raise HTTPException(status_code=400, detail="Account code already exists for this company.")
        account = Account(**data.model_dump())
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        await event_bus.publish("account.created", data.model_dump(), source_module="accounting")
        return account

    async def get_account(self, account_id: UUID):
        account = await self.db.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return account

    async def list_accounts(self, search: Optional[str] = None, skip: int = 0, limit: int = 20):
        stmt = select(Account)
        if search:
            stmt = stmt.where(
                or_(
                    Account.account_code.ilike(f"%{search}%"),
                    Account.account_name.ilike(f"%{search}%")
                )
            )
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        accounts = result.scalars().all()
        # Return as AccountListResponse for FastAPI response_model compatibility
        from app.modules.accounting.core.schemas.accounting_schemas import AccountListResponse
        return AccountListResponse(accounts=[AccountResponse.model_validate(account) for account in accounts], total=len(accounts))

    async def update_account(self, account_id: UUID, data: AccountUpdate):
        account = await self.get_account(account_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        await event_bus.publish("account.updated", {"id": str(account_id), **data.model_dump()}, source_module="accounting")
        return account

    async def delete_account(self, account_id: UUID):
        account = await self.get_account(account_id)
        if not account:
            return False
        await self.db.delete(account)
        await self.db.commit()
        if self.event_bus:
            await self.event_bus.publish("account.deleted", {"id": str(account_id)}, source_module="accounting")
        return True

    async def search_accounts(self, query: str) -> List[Account]:
        stmt = select(Account).where(Account.account_name.ilike(f"%{query}%"))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def bulk_create_accounts(self, accounts: List[AccountCreate]) -> List[Account]:
        created = []
        for data in accounts:
            account = Account(**data.model_dump())
            self.db.add(account)
            created.append(account)
        await self.db.commit()
        for account in created:
            await self.db.refresh(account)
        return created

    async def get_account_audit_log(self, account_id: UUID):
        stmt = select(BudgetAuditLog).where(BudgetAuditLog.budget_id == account_id)
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        return [
            {
                "action": log.action,
                "performed_by": log.performed_by,
                "performed_at": str(log.performed_at),
                "details": log.details
            } for log in logs
        ]

    async def set_account_active_status(self, account_id: UUID, is_active: bool):
        account = await self.get_account(account_id)
        account.is_active = is_active
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def create_budget_allocation_line(self, allocation_id: UUID, data: BudgetAllocationLineCreate):
        line = BudgetAllocationLine(**data.model_dump(), allocation_id=allocation_id)
        self.db.add(line)
        await self.db.commit()
        await self.db.refresh(line)
        if self.event_bus:
            await self.event_bus.publish("budget_allocation_line.created", {"id": str(line.id), "allocation_id": str(allocation_id)}, source_module="accounting")
        return line

    async def get_budget_allocation_line(self, line_id: UUID):
        line = await self.db.get(BudgetAllocationLine, line_id)
        if not line:
            raise HTTPException(status_code=404, detail="Budget allocation line not found")
        return line

    async def list_budget_allocation_lines(self, allocation_id: UUID, skip: int = 0, limit: int = 100):
        stmt = select(BudgetAllocationLine).where(BudgetAllocationLine.allocation_id == allocation_id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        lines = result.scalars().all()
        return lines

    async def update_budget_allocation_line(self, line_id: UUID, data: BudgetAllocationLineUpdate):
        line = await self.get_budget_allocation_line(line_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(line, field, value)
        self.db.add(line)
        await self.db.commit()
        await self.db.refresh(line)
        if self.event_bus:
            await self.event_bus.publish("budget_allocation_line.updated", {"id": str(line.id)}, source_module="accounting")
        return line

    async def delete_budget_allocation_line(self, line_id: UUID):
        line = await self.get_budget_allocation_line(line_id)
        await self.db.delete(line)
        await self.db.commit()
        if self.event_bus:
            await self.event_bus.publish("budget_allocation_line.deleted", {"id": str(line_id)}, source_module="accounting")
        return True

    async def create_budget_template(self, data: BudgetTemplateCreate) -> BudgetTemplate:
        # Validate company exists
        company = await self.db.execute(select(Company).where(Company.id == data.company_id))
        if not company.scalar_one_or_none():
            raise ValueError("Company not found")
        # Check for unique template_code
        existing = await self.db.execute(select(BudgetTemplate).where(BudgetTemplate.template_code == data.template_code, BudgetTemplate.company_id == data.company_id))
        if existing.scalar_one_or_none():
            raise ValueError("Template code already exists for this company")
        template = BudgetTemplate(**data.model_dump())
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_budget_template(self, template_id: UUID) -> BudgetTemplate:
        result = await self.db.execute(select(BudgetTemplate).where(BudgetTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("Budget template not found")
        return template

    async def list_budget_templates(self, company_id: UUID, skip: int = 0, limit: int = 20) -> List[BudgetTemplate]:
        stmt = select(BudgetTemplate).where(BudgetTemplate.company_id == company_id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_budget_template(self, template_id: UUID, data: BudgetTemplateUpdate) -> BudgetTemplate:
        result = await self.db.execute(select(BudgetTemplate).where(BudgetTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("Budget template not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(template, key, value)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_budget_template(self, template_id: UUID) -> None:
        result = await self.db.execute(select(BudgetTemplate).where(BudgetTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("Budget template not found")
        await self.db.delete(template)
        await self.db.commit()

    async def update_budget_variance(self, variance_id: UUID, data: BudgetVarianceUpdate):
        """Update an existing budget variance"""
        from app.modules.accounting.core.models.accounting_models import BudgetVariance

        # Get the existing variance
        result = await self.db.execute(
            select(BudgetVariance).where(BudgetVariance.id == variance_id)
        )
        variance = result.scalar_one_or_none()
        if not variance:
            raise HTTPException(status_code=404, detail="Budget variance not found")

        # Update fields with provided data
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(variance, field, value)

        # Save changes
        self.db.add(variance)
        await self.db.commit()
        await self.db.refresh(variance)

        # Publish event if event bus is available
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetvariance.updated", 
                {"budget_variance_id": str(variance_id)}
            )

        return variance
    
    async def delete_budget_variance(self, variance_id: UUID):
        """Delete a budget variance"""
        from app.modules.accounting.core.models.accounting_models import BudgetVariance
        
        # Get the existing variance
        result = await self.db.execute(
            select(BudgetVariance).where(BudgetVariance.id == variance_id)
        )
        variance = result.scalar_one_or_none()
        if not variance:
            raise HTTPException(status_code=404, detail="Budget variance not found")
        
        # Delete the variance
        await self.db.delete(variance)
        await self.db.commit()
        
        # Publish event if event bus is available
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetvariance.deleted", 
                {"budget_variance_id": str(variance_id)}
            )
        
        return True
    
    # --- Budget Audit Log CRUD ---
    async def create_budget_audit_log(self, data: BudgetAuditLogCreate, budget_id: UUID):
        """Create a new budget audit log entry"""
        from app.modules.accounting.core.models.accounting_models import BudgetAuditLog, Budget
        
        # Validate that budget exists
        budget_result = await self.db.execute(
            select(Budget).where(Budget.id == budget_id)
        )
        budget = budget_result.scalar_one_or_none()
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Create the audit log entry
        log_data = data.model_dump()
        log_data["budget_id"] = budget_id
        new_log = BudgetAuditLog(**log_data)
        self.db.add(new_log)
        await self.db.commit()
        await self.db.refresh(new_log)
        
        # Publish event if event bus is available
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetauditlog.created", 
                {"budget_audit_log_id": str(new_log.id), "budget_id": str(budget_id)}
            )
        
        return new_log

    async def get_budget_audit_log(self, log_id: UUID):
        """Get a single budget audit log entry"""
        from app.modules.accounting.core.models.accounting_models import BudgetAuditLog
        
        result = await self.db.execute(
            select(BudgetAuditLog).where(BudgetAuditLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail="Budget audit log not found")
        
        return log

    async def list_budget_audit_logs(
        self, 
        budget_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        action: Optional[str] = None,
        performed_by: Optional[UUID] = None
    ):
        """List all audit logs for a budget"""
        from app.modules.accounting.core.models.accounting_models import BudgetAuditLog
        
        stmt = select(BudgetAuditLog).where(BudgetAuditLog.budget_id == budget_id)
        
        # Apply filters
        if action:
            stmt = stmt.where(BudgetAuditLog.action.ilike(f"%{action}%"))
        if performed_by:
            stmt = stmt.where(BudgetAuditLog.performed_by == performed_by)
        
        # Apply pagination and ordering
        stmt = stmt.offset(skip).limit(limit).order_by(BudgetAuditLog.performed_at.desc())
        
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        
        return logs

    async def update_budget_audit_log(self, log_id: UUID, data: BudgetAuditLogUpdate):
        """Update a budget audit log entry"""
        from app.modules.accounting.core.models.accounting_models import BudgetAuditLog
        
        result = await self.db.execute(
            select(BudgetAuditLog).where(BudgetAuditLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail="Budget audit log not found")
        
        # Update fields
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(log, field, value)
        
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        
        # Publish event if event bus is available
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetauditlog.updated", 
                {"budget_audit_log_id": str(log_id)}
            )
        
        return log

    async def delete_budget_audit_log(self, log_id: UUID):
        """Delete a budget audit log entry"""
        from app.modules.accounting.core.models.accounting_models import BudgetAuditLog
        
        result = await self.db.execute(
            select(BudgetAuditLog).where(BudgetAuditLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail="Budget audit log not found")
        
        await self.db.delete(log)
        await self.db.commit()
        
        # Publish event if event bus is available
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetauditlog.deleted", 
                {"budget_audit_log_id": str(log_id)}
            )
        
        return True

    async def get_budget_audit_summary(self, budget_id: UUID):
        """Get audit summary for a budget"""
        from app.modules.accounting.core.models.accounting_models import BudgetAuditLog
        
        # Get action counts
        action_counts = await self.db.execute(
            select(
                BudgetAuditLog.action,
                func.count(BudgetAuditLog.id).label('count')
            ).where(
                BudgetAuditLog.budget_id == budget_id
            ).group_by(BudgetAuditLog.action)
        )
        
        # Get recent activities
        recent_activities = await self.db.execute(
            select(BudgetAuditLog).where(
                BudgetAuditLog.budget_id == budget_id
            ).order_by(BudgetAuditLog.performed_at.desc()).limit(10)
        )
        
        return {
            "budget_id": str(budget_id),
            "action_counts": [{"action": row.action, "count": row.count} for row in action_counts],
            "recent_activities": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "performed_by": str(log.performed_by) if log.performed_by else None,
                    "performed_at": log.performed_at.isoformat() if log.performed_at else None,
                    "details": log.details
                }
                for log in recent_activities.scalars().all()
            ]
        }

class CostCenterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_cost_center(self, company_id: UUID, data: CostCenterCreate):
        # Remove company_id from data if present to avoid duplicate keyword arguments
        data_dict = data.model_dump()
        data_dict.pop('company_id', None)
        cost_center = CostCenter(company_id=company_id, **data_dict)
        self.db.add(cost_center)
        await self.db.commit()
        await self.db.refresh(cost_center)
        await event_bus.publish("cost_center.created", cost_center, source_module="accounting")
        return cost_center

    async def get_cost_center(self, cost_center_id: UUID):
        cost_center = await self.db.get(CostCenter, cost_center_id)
        if not cost_center:
            raise HTTPException(status_code=404, detail="Cost center not found")
        return cost_center

    async def list_cost_centers(self, skip: int = 0, limit: int = 100) -> List[CostCenter]:
        stmt = select(CostCenter).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_cost_center(self, cost_center_id: UUID, data: CostCenterUpdate):
        cost_center = await self.get_cost_center(cost_center_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(cost_center, field, value)
        self.db.add(cost_center)
        await self.db.commit()
        await self.db.refresh(cost_center)
        await event_bus.publish("cost_center.updated", {"id": str(cost_center_id), **data.model_dump()}, source_module="accounting")
        return cost_center

    async def delete_cost_center(self, cost_center_id: UUID):
        cost_center = await self.get_cost_center(cost_center_id)
        await self.db.delete(cost_center)
        await self.db.commit()
        await event_bus.publish("cost_center.deleted", {"id": str(cost_center_id)}, source_module="accounting")

class FiscalYearService:
    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus

    async def create_fiscal_year(self, data: FiscalYearCreate):
        fiscal_year = FiscalYear(**data.model_dump())
        self.db.add(fiscal_year)
        await self.db.commit()
        await self.db.refresh(fiscal_year)
        if self.event_bus:
            await self.event_bus.publish(AccountingEventTypes.FISCAL_YEAR_CREATED, {"fiscal_year_id": str(fiscal_year.id)})
        return fiscal_year

    async def get_fiscal_year(self, fiscal_year_id: UUID):
        fiscal_year = await self.db.get(FiscalYear, fiscal_year_id)
        if not fiscal_year:
            raise HTTPException(status_code=404, detail="Fiscal year not found")
        return fiscal_year

    async def list_fiscal_years(self, skip: int = 0, limit: int = 100) -> List[FiscalYear]:
        stmt = select(FiscalYear).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_fiscal_year(self, fiscal_year_id: UUID, data: FiscalYearUpdate):
        fiscal_year = await self.get_fiscal_year(fiscal_year_id)
        was_closed = fiscal_year.is_closed
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(fiscal_year, field, value)
        self.db.add(fiscal_year)
        await self.db.commit()
        await self.db.refresh(fiscal_year)
        closed = not was_closed and fiscal_year.is_closed
        if self.event_bus:
            await self.event_bus.publish(AccountingEventTypes.FISCAL_YEAR_UPDATED, {"fiscal_year_id": str(fiscal_year_id)})
            if closed:
                await self.event_bus.publish(AccountingEventTypes.FISCAL_YEAR_CLOSED, {"fiscal_year_id": str(fiscal_year_id)})
        return fiscal_year, closed

    async def delete_fiscal_year(self, fiscal_year_id: UUID):
        fiscal_year = await self.get_fiscal_year(fiscal_year_id)
        await self.db.delete(fiscal_year)
        await self.db.commit()
        # Optionally publish delete event
        if self.event_bus:
            await self.event_bus.publish("accounting.fiscal_year.deleted", {"fiscal_year_id": str(fiscal_year_id)})

    async def list_periods(self, fiscal_year_id: UUID):
        stmt = select(FiscalPeriod).where(FiscalPeriod.fiscal_year_id == fiscal_year_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_period(self, fiscal_year_id: UUID, period_data: FiscalPeriodCreate):
        # Accepts a Pydantic model, so dates are already date objects
        data = period_data.model_dump()
        data.pop("fiscal_year_id", None)
        period = FiscalPeriod(fiscal_year_id=fiscal_year_id, **data)
        self.db.add(period)
        await self.db.commit()
        await self.db.refresh(period)
        if self.event_bus:
            await self.event_bus.publish(AccountingEventTypes.FISCAL_PERIOD_CREATED, {"fiscal_year_id": str(fiscal_year_id), "period_id": str(period.id)})
        return period

    # Add update/delete for periods as needed

class FiscalPeriodService:
    def __init__(self, db: AsyncSession, event_bus: EventBus = None):
        self.db = db
        self.event_bus = event_bus

    async def create_fiscal_period(self, data: FiscalPeriodCreate):
        fiscal_period = FiscalPeriod(**data.model_dump())
        self.db.add(fiscal_period)
        await self.db.commit()
        await self.db.refresh(fiscal_period)
        if self.event_bus:
            await self.event_bus.publish(AccountingEventTypes.FISCAL_PERIOD_CREATED, {"fiscal_period_id": str(fiscal_period.id), **data.model_dump()}, source_module="accounting")
        return fiscal_period

    async def get_fiscal_period(self, fiscal_period_id: UUID):
        fiscal_period = await self.db.get(FiscalPeriod, fiscal_period_id)
        if not fiscal_period:
            raise HTTPException(status_code=404, detail="Fiscal period not found")
        return fiscal_period

    async def list_fiscal_periods(self, skip: int = 0, limit: int = 100) -> List[FiscalPeriod]:
        stmt = select(FiscalPeriod).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_fiscal_period(self, fiscal_period_id: UUID, data: FiscalPeriodUpdate):
        fiscal_period = await self.get_fiscal_period(fiscal_period_id)
        if fiscal_period.is_closed:
            raise HTTPException(status_code=400, detail="Cannot update a closed fiscal period.")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(fiscal_period, field, value)
        self.db.add(fiscal_period)
        await self.db.commit()
        await self.db.refresh(fiscal_period)
        if self.event_bus:
            await self.event_bus.publish(AccountingEventTypes.FISCAL_PERIOD_UPDATED, {"fiscal_period_id": str(fiscal_period_id), **data.model_dump()}, source_module="accounting")
        return fiscal_period

    async def close_fiscal_period(self, fiscal_period_id: UUID):
        fiscal_period = await self.get_fiscal_period(fiscal_period_id)
        if fiscal_period.is_closed:
            raise HTTPException(status_code=400, detail="Fiscal period is already closed.")
        fiscal_period.is_closed = True
        self.db.add(fiscal_period)
        await self.db.commit()
        await self.db.refresh(fiscal_period)
        if self.event_bus:
            await self.event_bus.publish(AccountingEventTypes.FISCAL_PERIOD_CLOSED, {"fiscal_period_id": str(fiscal_period_id)}, source_module="accounting")
        return fiscal_period

    async def delete_fiscal_period(self, fiscal_period_id: UUID):
        fiscal_period = await self.get_fiscal_period(fiscal_period_id)
        if fiscal_period.is_closed:
            raise HTTPException(status_code=400, detail="Cannot delete a closed fiscal period.")
        await self.db.delete(fiscal_period)
        await self.db.commit()
        if self.event_bus:
            await self.event_bus.publish(AccountingEventTypes.FISCAL_PERIOD_DELETED, {"fiscal_period_id": str(fiscal_period_id)}, source_module="accounting")
        return True

    async def update_period(self, period_id: UUID, update_data: FiscalPeriodUpdate, user=None):
        period = await self.db.get(FiscalPeriod, period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Fiscal period not found")
        if getattr(period, "is_closed", False):
            raise HTTPException(status_code=400, detail="Cannot update a closed fiscal period")
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(period, key, value)
        self.db.add(period)
        await self.db.commit()
        await self.db.refresh(period)
        if self.event_bus:
            await self.event_bus.publish(
                AccountingEventTypes.FISCAL_PERIOD_UPDATED,
                {"period_id": str(period.id), "updated_by": getattr(user, "id", None)}
            )
        return period

    async def delete_period(self, period_id: UUID, user=None):
        period = await self.db.get(FiscalPeriod, period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Fiscal period not found")
        if getattr(period, "is_closed", False):
            raise HTTPException(status_code=400, detail="Cannot delete a closed fiscal period")
        await self.db.delete(period)
        await self.db.commit()
        if self.event_bus:
            await self.event_bus.publish(
                AccountingEventTypes.FISCAL_PERIOD_DELETED,
                {"period_id": str(period.id), "deleted_by": getattr(user, "id", None)}
            )
        return {"detail": "Fiscal period deleted"}

class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_company(self, data: CompanyCreate):
        # Validate parent company exists if provided
        if data.parent_company_id:
            parent_stmt = select(Company).where(Company.id == data.parent_company_id)
            parent_result = await self.db.execute(parent_stmt)
            parent_company = parent_result.scalar_one_or_none()
            if not parent_company:
                raise HTTPException(status_code=400, detail=f"Parent company with ID {data.parent_company_id} not found")
        
        company = Company(**data.model_dump())
        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)
        await event_bus.publish("company.created", data.model_dump(), source_module="accounting")
        return company

    async def list_companies(self, skip=0, limit=100):
        q = await self.db.execute(select(Company).offset(skip).limit(limit))
        return q.scalars().all()

    async def get_company(self, company_id):
        q = await self.db.execute(select(Company).where(Company.id == company_id))
        return q.scalar_one_or_none()

    async def update_company(self, company_id, data):
        company = await self.get_company(company_id)
        if not company:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(company, k, v)
        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)
        await event_bus.publish("company.updated", {"id": str(company_id), **data.model_dump()}, source_module="accounting")
        return company

    async def delete_company(self, company_id):
        company = await self.get_company(company_id)
        if not company:
            return None
        await self.db.delete(company)
        await self.db.commit()
        await event_bus.publish("company.deleted", {"id": str(company_id)}, source_module="accounting")
        return True

class CurrencyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_currency(self, data):
        currency = Currency(**data.model_dump())
        self.db.add(currency)
        await self.db.commit()
        await self.db.refresh(currency)
        await event_bus.publish("currency.created", data.model_dump(), source_module="accounting")
        return currency

    async def list_currencies(self, skip=0, limit=100):
        q = await self.db.execute(select(Currency).offset(skip).limit(limit))
        return q.scalars().all()

    async def get_currency(self, currency_id):
        q = await self.db.execute(select(Currency).where(Currency.id == currency_id))
        return q.scalar_one_or_none()

    async def update_currency(self, currency_id, data):
        currency = await self.get_currency(currency_id)
        if not currency:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(currency, k, v)
        self.db.add(currency)
        await self.db.commit()
        await self.db.refresh(currency)
        await event_bus.publish("currency.updated", {"id": str(currency_id), **data.model_dump()}, source_module="accounting")
        return currency

    async def delete_currency(self, currency_id):
        currency = await self.get_currency(currency_id)
        if not currency:
            return None
        await self.db.delete(currency)
        await self.db.commit()
        await event_bus.publish("currency.deleted", {"id": str(currency_id)}, source_module="accounting")
        return True

class ProfitCenterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profit_center(self, data: ProfitCenterCreate):
        await event_bus.publish("profit_center.created", data.model_dump(), source_module="accounting")

    async def get_profit_center(self, profit_center_id: UUID):
        pass

    async def update_profit_center(self, profit_center_id: UUID, data: ProfitCenterUpdate):
        await event_bus.publish("profit_center.updated", {"id": str(profit_center_id), **data.model_dump()}, source_module="accounting")

    async def delete_profit_center(self, profit_center_id: UUID):
        await event_bus.publish("profit_center.deleted", {"id": str(profit_center_id)}, source_module="accounting")

class LedgerAccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_account(self, data: AccountCreate):
        await event_bus.publish("account.created", data.model_dump(), source_module="accounting")

    async def get_account(self, account_id: UUID):
        pass

    async def update_account(self, account_id: UUID, data: AccountUpdate):
        await event_bus.publish("account.updated", {"id": str(account_id), **data.model_dump()}, source_module="accounting")

    async def delete_account(self, account_id: UUID):
        await event_bus.publish("account.deleted", {"id": str(account_id)}, source_module="accounting")

from app.modules.accounting.core.models.accounting_models import JournalEntry, JournalEntryLine
from app.modules.accounting.core.schemas.accounting_schemas import JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse, JournalEntryLineCreate
from sqlalchemy.exc import NoResultFound
from sqlalchemy import update, delete
import datetime

class JournalEntryService:
    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus or EventBus()

    async def create_journal_entry(self, data: JournalEntryCreate):
        # Auto-generate entry_number if not provided, ensure uniqueness per company
        entry_number = getattr(data, 'entry_number', None)
        today = data.entry_date if hasattr(data, 'entry_date') and data.entry_date else datetime.date.today()
        if not entry_number:
            # Find max sequence for this company and date
            from sqlalchemy import desc
            prefix = f"JE-{today.strftime('%Y%m%d')}-"
            stmt = select(JournalEntry.entry_number).where(
                JournalEntry.company_id == data.company_id,
                JournalEntry.entry_number.like(f"{prefix}%")
            ).order_by(desc(JournalEntry.entry_number)).limit(1)
            result = await self.db.execute(stmt)
            last_entry_number = result.scalar()
            if last_entry_number:
                try:
                    last_seq = int(last_entry_number.split('-')[-1])
                except Exception:
                    last_seq = 0
            else:
                last_seq = 0
            entry_number = f"{prefix}{last_seq+1:03d}"
        else:
            # Check uniqueness for custom entry_number
            stmt = select(JournalEntry).where(
                JournalEntry.company_id == data.company_id,
                JournalEntry.entry_number == entry_number
            )
            result = await self.db.execute(stmt)
            if result.scalar():
                raise HTTPException(status_code=400, detail="entry_number already exists for this company.")

        # Prepare lines with line_number, company_id, and amount mapping
        lines = []
        for idx, line_data in enumerate(data.lines, start=1):
            line_dict = line_data.dict() if hasattr(line_data, 'dict') else dict(line_data)
            line_dict['line_number'] = idx
            # Always set company_id from parent
            line_dict['company_id'] = data.company_id
            # Map 'amount' to debit_amount/credit_amount if present
            if 'amount' in line_dict:
                amt = line_dict.pop('amount')
                if amt >= 0:
                    line_dict['debit_amount'] = amt
                    line_dict['credit_amount'] = 0
                else:
                    line_dict['debit_amount'] = 0
                    line_dict['credit_amount'] = abs(amt)
            if 'debit_amount' not in line_dict:
                line_dict['debit_amount'] = 0
            if 'credit_amount' not in line_dict:
                line_dict['credit_amount'] = 0
            lines.append(JournalEntryLine(**line_dict))

        # Create the entry and assign lines before flush
        entry = JournalEntry(
            company_id=data.company_id,
            entry_number=entry_number,
            entry_date=data.entry_date,
            description=data.description,
            reference_number=getattr(data, 'reference_number', None),
            fiscal_period_id=data.fiscal_period_id,
            lines=lines,  # assign here!
            # ...other fields as needed...
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        await self.event_bus.publish("journal_entry.created", {"id": str(entry.id)}, source_module="accounting")
        # Eagerly load lines to avoid async lazy-load error in response serialization
        from sqlalchemy.orm import selectinload
        stmt = select(JournalEntry).options(selectinload(JournalEntry.lines)).where(JournalEntry.id == entry.id)
        result = await self.db.execute(stmt)
        entry_with_lines = result.scalar_one()
        return entry_with_lines

    async def get_journal_entry(self, entry_id: UUID):
        entry = await self.db.get(JournalEntry, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="JournalEntry not found")
        return entry

    async def list_journal_entries(self, skip: int = 0, limit: int = 100):
        stmt = select(JournalEntry).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_journal_entry(self, entry_id: UUID, data: JournalEntryUpdate):
        entry = await self.db.get(JournalEntry, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="JournalEntry not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "lines":
                continue  # handled below
            setattr(entry, field if field != "entry_date" else "entry_date", value)
        if data.lines is not None:
            # Delete old lines
            await self.db.execute(delete(JournalEntryLine).where(JournalEntryLine.journal_entry_id == entry_id))
            # Add new lines
            lines = []
            for idx, line_data in enumerate(data.lines, start=1):
                line_dict = line_data.dict() if hasattr(line_data, 'dict') else dict(line_data)
                line_dict['line_number'] = idx
                # Map 'amount' to debit_amount/credit_amount if present
                if 'amount' in line_dict:
                    amt = line_dict.pop('amount')
                    if amt >= 0:
                        line_dict['debit_amount'] = amt
                        line_dict['credit_amount'] = 0
                    else:
                        line_dict['debit_amount'] = 0
                        line_dict['credit_amount'] = abs(amt)
                if 'debit_amount' not in line_dict:
                    line_dict['debit_amount'] = 0
                if 'credit_amount' not in line_dict:
                    line_dict['credit_amount'] = 0
                lines.append(JournalEntryLine(**line_dict))
            entry.lines = lines
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def delete_journal_entry(self, entry_id: UUID):
        entry = await self.db.get(JournalEntry, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="JournalEntry not found")
        await self.db.execute(delete(JournalEntryLine).where(JournalEntryLine.journal_entry_id == entry_id))
        await self.db.delete(entry)
        await self.db.commit()
        await self.event_bus.publish("journal_entry.deleted", {"id": str(entry_id)}, source_module="accounting")
        return True

    async def get_journal_entry_line(self, line_id: UUID):
        line = await self.db.get(JournalEntryLine, line_id)
        if not line:
            return None
        return line

    async def create_journal_entry_line(self, data: JournalEntryLineCreate):
        # Find the parent journal entry to get company_id and next line_number
        journal_entry_id = getattr(data, 'journal_entry_id', None)
        if not journal_entry_id:
            raise HTTPException(status_code=400, detail="journal_entry_id is required")
        entry = await self.db.get(JournalEntry, journal_entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Parent JournalEntry not found")
        # Find max line_number for this entry
        stmt = select(func.max(JournalEntryLine.line_number)).where(JournalEntryLine.journal_entry_id == journal_entry_id)
        result = await self.db.execute(stmt)
        max_line_number = result.scalar() or 0
        line_dict = data.dict()
        line_dict['line_number'] = max_line_number + 1
        line_dict['company_id'] = entry.company_id
        # Map amount to debit/credit
        if 'amount' in line_dict:
            amt = line_dict.pop('amount')
            if amt >= 0:
                line_dict['debit_amount'] = amt
                line_dict['credit_amount'] = 0
            else:
                line_dict['debit_amount'] = 0
                line_dict['credit_amount'] = abs(amt)
        if 'debit_amount' not in line_dict:
            line_dict['debit_amount'] = 0
        if 'credit_amount' not in line_dict:
            line_dict['credit_amount'] = 0
        line = JournalEntryLine(**line_dict)
        self.db.add(line)
        await self.db.commit()
        await self.db.refresh(line)
        return line

    async def update_journal_entry_line(self, line_id: UUID, data: JournalEntryLineCreate):
        line = await self.db.get(JournalEntryLine, line_id)
        if not line:
            return None
        # Only update allowed fields
        update_dict = data.dict(exclude_unset=True)
        # Map amount to debit/credit
        if 'amount' in update_dict:
            amt = update_dict.pop('amount')
            if amt >= 0:
                update_dict['debit_amount'] = amt
                update_dict['credit_amount'] = 0
            else:
                update_dict['debit_amount'] = 0
                update_dict['credit_amount'] = abs(amt)
        for k, v in update_dict.items():
            setattr(line, k, v)
        await self.db.commit()
        await self.db.refresh(line)
        return line

    async def delete_journal_entry_line(self, line_id: UUID):
        line = await self.db.get(JournalEntryLine, line_id)
        if not line:
            return None
        await self.db.delete(line)
        await self.db.commit()
        return True

    # Add these methods to the AccountingService class (around line 750)

    # --- Budget Variance CRUD ---
    async def create_budget_variance(self, data: BudgetVarianceCreate):
        from app.modules.accounting.core.models.accounting_models import BudgetVariance, BudgetLine
        
        # Validate that budget_line_id exists
        budget_line_result = await self.db.execute(
            select(BudgetLine).where(BudgetLine.id == data.budget_line_id)
        )
        budget_line = budget_line_result.scalar_one_or_none()
        if not budget_line:
            raise HTTPException(status_code=404, detail="Budget line not found")
        
        # Validate that fiscal_period_id exists if provided
        if data.fiscal_period_id:
            fiscal_period_result = await self.db.execute(
                select(FiscalPeriod).where(FiscalPeriod.id == data.fiscal_period_id)
            )
            fiscal_period = fiscal_period_result.scalar_one_or_none()
            if not fiscal_period:
                raise HTTPException(status_code=404, detail="Fiscal period not found")
        
        # Create the budget variance
        variance_data = data.model_dump()
        new_variance = BudgetVariance(**variance_data)
        self.db.add(new_variance)
        await self.db.commit()
        await self.db.refresh(new_variance)
        
        # Publish event if event bus is available
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetvariance.created", 
                {"budget_variance_id": str(new_variance.id)}
            )
        
        return new_variance

    async def update_budget_variance(self, variance_id: UUID, data: BudgetVarianceUpdate):
        from app.modules.accounting.core.models.accounting_models import BudgetVariance
        
        result = await self.db.execute(
            select(BudgetVariance).where(BudgetVariance.id == variance_id)
        )
        variance = result.scalar_one_or_none()
        if not variance:
            raise HTTPException(status_code=404, detail="Budget variance not found")
        
        # Update fields
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(variance, field, value)
        
        self.db.add(variance)
        await self.db.commit()
        await self.db.refresh(variance)
        
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetvariance.updated", 
                {"budget_variance_id": str(variance_id)}
            )
        
        return variance

    async def delete_budget_variance(self, variance_id: UUID):
        from app.modules.accounting.core.models.accounting_models import BudgetVariance
        
        result = await self.db.execute(
            select(BudgetVariance).where(BudgetVariance.id == variance_id)
        )
        variance = result.scalar_one_or_none()
        if not variance:
            raise HTTPException(status_code=404, detail="Budget variance not found")
        
        await self.db.delete(variance)
        await self.db.commit()
        
        if self.event_bus:
            await self.event_bus.publish(
                "accounting.budgetvariance.deleted", 
                {"budget_variance_id": str(variance_id)}
            )
        
        return True

    async def get_budget_variance(self, variance_id: UUID):
        from app.modules.accounting.core.models.accounting_models import BudgetVariance
        
        result = await self.db.execute(
            select(BudgetVariance).where(BudgetVariance.id == variance_id)
        )
        variance = result.scalar_one_or_none()
        if not variance:
            raise HTTPException(status_code=404, detail="Budget variance not found")
        
        return variance

    async def list_budget_variances(self, budget_line_id: Optional[UUID] = None, skip: int = 0, limit: int = 100):
        from app.modules.accounting.core.models.accounting_models import BudgetVariance
        
        stmt = select(BudgetVariance)
        if budget_line_id:
            stmt = stmt.where(BudgetVariance.budget_line_id == budget_line_id)
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
