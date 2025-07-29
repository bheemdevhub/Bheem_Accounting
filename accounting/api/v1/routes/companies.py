# app/modules/accounting/api/v1/routes/companies.py
"""Company and Org Chart API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID, uuid4
from datetime import datetime

from app.modules.auth.core.services.permissions_service import require_roles, require_api_permission, get_current_user
from app.modules.accounting.core.schemas.accounting_schemas import CompanyCreate, CompanyResponse
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.models import Company as CompanyModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, or_, and_
from app.core.event_bus import EventBus
from app.modules.accounting.core.models.accounting_models import ProfitCenter, CostCenter
from app.modules.accounting.core.schemas.accounting_schemas import (
    ProfitCenterResponse, ProfitCenterCreate, ProfitCenterUpdate, CostCenterResponse, CostCenterCreate, CostCenterUpdate
)

event_bus_instance = EventBus()

def get_event_bus():
    return event_bus_instance

router = APIRouter(prefix="/companies", tags=["Companies"])

@router.get("/", summary="List all companies", response_model=List[CompanyResponse], dependencies=[Depends(require_roles("Admin", "Accountant", "Viewer"))])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    search: str = None,
    company_type: str = None,
    is_active: bool = None,
    offset: int = 0,
    limit: int = 20
):
    query = select(CompanyModel)
    filters = []
    # Filtering
    if search:
        filters.append(or_(
            CompanyModel.company_name.ilike(f"%{search}%"),
            CompanyModel.company_code.ilike(f"%{search}%"),
            CompanyModel.legal_name.ilike(f"%{search}%")
        ))
    if company_type:
        filters.append(CompanyModel.company_type == company_type)
    if is_active is not None:
        filters.append(CompanyModel.is_active == is_active)
    if filters:
        query = query.where(and_(*filters))
    # Pagination
    query = query.order_by(CompanyModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    companies = result.scalars().all()
    return [
        CompanyResponse(
            id=row.id,
            company_code=row.company_code,
            company_name=row.company_name,
            legal_name=getattr(row, 'legal_name', None),
            company_type=row.company_type,
            parent_company_id=getattr(row, 'parent_company_id', None),
            functional_currency_id=getattr(row, 'functional_currency_id', None),
            reporting_currency_id=getattr(row, 'reporting_currency_id', None),
            consolidation_method=getattr(row, 'consolidation_method', None),
            address=getattr(row, 'address', None),
            tax_id=getattr(row, 'tax_id', None),
            registration_number=getattr(row, 'registration_number', None),
            is_active=row.is_active,
            created_at=getattr(row, 'created_at', None),
            updated_at=getattr(row, 'updated_at', None)
        ) for row in companies
    ]

@router.post("/", summary="Create a new company", response_model=CompanyResponse, status_code=201)
async def create_company(company: CompanyCreate, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    from uuid import uuid4
    from datetime import datetime
    import logging
    # Ensure ID and timestamps
    company_id = getattr(company, "id", None) or str(uuid4())
    now = datetime.utcnow()
    db_company = CompanyModel(
        id=company_id,
        company_code=company.company_code,
        company_name=company.company_name,
        legal_name=company.legal_name,
        company_type=company.company_type,
        parent_company_id=company.parent_company_id,
        functional_currency_id=company.functional_currency_id,
        reporting_currency_id=company.reporting_currency_id,
        consolidation_method=company.consolidation_method,
        address=company.address,
        tax_id=company.tax_id,
        registration_number=company.registration_number,
        is_active=company.is_active if company.is_active is not None else True,
        created_at=getattr(company, "created_at", now),
        updated_at=getattr(company, "updated_at", now)
    )
    db.add(db_company)
    try:
        await db.commit()
        await db.refresh(db_company)
        # Log after commit
        logging.info(f"Company committed successfully: {db_company.id}")
        # Log company count in DB
        result = await db.execute(select(CompanyModel))
        companies = result.scalars().all()
        logging.info(f"Company count after commit: {len(companies)}")
    except IntegrityError as ie:
        await db.rollback()
        logging.error(f"IntegrityError while creating company: {ie}")
        logging.error(f"Company data: {db_company.__dict__}")
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(ie)}")
    except Exception as e:
        await db.rollback()
        logging.error(f"Exception while creating company: {e}")
        logging.error(f"Company data: {db_company.__dict__}")
        import traceback
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create company: {str(e)}")
    await event_bus.publish("company.created", {"company_id": str(db_company.id), "company_code": db_company.company_code})
    return CompanyResponse(
        id=db_company.id,
        company_code=db_company.company_code,
        company_name=db_company.company_name,
        legal_name=db_company.legal_name,
        company_type=db_company.company_type,
        parent_company_id=db_company.parent_company_id,
        functional_currency_id=db_company.functional_currency_id,
        reporting_currency_id=db_company.reporting_currency_id,
        consolidation_method=db_company.consolidation_method,
        address=db_company.address,
        tax_id=db_company.tax_id,
        registration_number=db_company.registration_number,
        is_active=db_company.is_active,
        created_at=getattr(db_company, 'created_at', None),
        updated_at=getattr(db_company, 'updated_at', None)
    )

@router.get("/{company_id}", summary="Get company details", response_model=CompanyResponse, dependencies=[Depends(require_roles("Admin", "Accountant", "Viewer"))])
async def get_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompanyModel).where(CompanyModel.id == str(company_id)))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyResponse(
        id=company.id,
        company_code=company.company_code,
        company_name=company.company_name,
        legal_name=getattr(company, 'legal_name', None),
        company_type=company.company_type,
        parent_company_id=getattr(company, 'parent_company_id', None),
        functional_currency_id=getattr(company, 'functional_currency_id', None),
        reporting_currency_id=getattr(company, 'reporting_currency_id', None),
        consolidation_method=getattr(company, 'consolidation_method', None),
        address=getattr(company, 'address', None),
        tax_id=getattr(company, 'tax_id', None),
        registration_number=getattr(company, 'registration_number', None),
        is_active=company.is_active,
        created_at=getattr(company, 'created_at', None),
        updated_at=getattr(company, 'updated_at', None)
    )

@router.put("/{company_id}", summary="Update company", response_model=CompanyResponse, dependencies=[Depends(require_roles("Admin"))])
async def update_company(company_id: UUID, company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompanyModel).where(CompanyModel.id == str(company_id)))
    db_company = result.scalar_one_or_none()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    update_data = company.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_company, k, v)
    try:
        await db.commit()
        await db.refresh(db_company)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Company code already exists.")
    return CompanyResponse(
        id=db_company.id,
        company_code=db_company.company_code,
        company_name=db_company.company_name,
        legal_name=db_company.legal_name,
        company_type=db_company.company_type,
        parent_company_id=db_company.parent_company_id,
        functional_currency_id=db_company.functional_currency_id,
        reporting_currency_id=db_company.reporting_currency_id,
        consolidation_method=db_company.consolidation_method,
        address=db_company.address,
        tax_id=db_company.tax_id,
        registration_number=db_company.registration_number,
        is_active=db_company.is_active,
        created_at=getattr(db_company, 'created_at', None),
        updated_at=getattr(db_company, 'updated_at', None)
    )

@router.delete("/{company_id}", summary="Delete company", dependencies=[Depends(require_roles("Admin")), Depends(get_current_user), Depends(lambda: require_api_permission("company.delete"))])
async def delete_company(company_id: UUID, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    result = await db.execute(select(CompanyModel).where(CompanyModel.id == str(company_id)))
    db_company = result.scalar_one_or_none()
    if not db_company:
        raise HTTPException(status_code=404, detail=f"Company not found for id: {company_id}")
    await db.delete(db_company)
    await db.commit()
    await event_bus.publish("company.deleted", {"company_id": str(company_id)})
    return {"detail": f"Company {company_id} deleted"}

# --- Profit Center APIs ---
@router.get("/{company_id}/profit-centers", response_model=List[ProfitCenterResponse], summary="List profit centers for a company", dependencies=[Depends(require_roles("Admin", "Accountant", "Viewer")), Depends(get_current_user), Depends(lambda: require_api_permission("profitcenter.read"))])
async def list_profit_centers(company_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProfitCenter).where(ProfitCenter.company_id == company_id))
    pcs = result.scalars().all()
    return [ProfitCenterResponse(**pc.__dict__) for pc in pcs]

@router.post("/{company_id}/profit-centers", response_model=ProfitCenterResponse, summary="Create profit center for a company", dependencies=[Depends(require_roles("Admin", "Accountant")), Depends(get_current_user), Depends(lambda: require_api_permission("profitcenter.create"))])
async def create_profit_center(company_id: UUID, pc: ProfitCenterCreate, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    pc_data = pc.dict()
    pc_data.pop("company_id", None)  # Remove company_id to avoid duplicate argument
    db_pc = ProfitCenter(company_id=company_id,
                        profit_center_code=pc.profit_center_code,
                        profit_center_name=pc.profit_center_name,
                        name=pc.name,
                        center_type=pc.center_type,  # <-- FIX: pass center_type
                        parent_profit_center_id=pc.parent_profit_center_id,
                        is_active=pc.is_active)
    db.add(db_pc)
    await db.commit()
    await db.refresh(db_pc)
    # Trigger event
    await event_bus.publish("profit_center.created", {"profit_center_id": str(db_pc.id), "company_id": str(company_id)})
    return ProfitCenterResponse(**db_pc.__dict__)

@router.get("/profit-centers/{profit_center_id}", response_model=ProfitCenterResponse, summary="Get profit center by ID", dependencies=[Depends(require_roles("Admin", "Accountant", "Viewer")), Depends(get_current_user), Depends(lambda: require_api_permission("profitcenter.read"))])
async def get_profit_center(profit_center_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProfitCenter).where(ProfitCenter.id == profit_center_id))
    pc = result.scalar_one_or_none()
    if not pc:
        raise HTTPException(status_code=404, detail="Profit center not found")
    # Ensure enum is serialized as value
    pc_dict = pc.__dict__.copy()
    if hasattr(pc, 'center_type') and pc.center_type is not None:
        pc_dict['center_type'] = pc.center_type.value if hasattr(pc.center_type, 'value') else pc.center_type
    return ProfitCenterResponse(**pc_dict)

@router.put("/profit-centers/{profit_center_id}", response_model=ProfitCenterResponse, summary="Update profit center", dependencies=[Depends(require_roles("Admin")), Depends(get_current_user), Depends(lambda: require_api_permission("profitcenter.update"))])
async def update_profit_center(profit_center_id: UUID, pc: ProfitCenterUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProfitCenter).where(ProfitCenter.id == profit_center_id))
    db_pc = result.scalar_one_or_none()
    if not db_pc:
        raise HTTPException(status_code=404, detail="Profit center not found")
    update_data = pc.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_pc, k, v)
    await db.commit()
    await db.refresh(db_pc)
    # Ensure enum is serialized as value
    db_pc_dict = db_pc.__dict__.copy()
    if hasattr(db_pc, 'center_type') and db_pc.center_type is not None:
        db_pc_dict['center_type'] = db_pc.center_type.value if hasattr(db_pc.center_type, 'value') else db_pc.center_type
    return ProfitCenterResponse(**db_pc_dict)

@router.delete("/profit-centers/{profit_center_id}", summary="Delete profit center", dependencies=[Depends(require_roles("Admin")), Depends(get_current_user), Depends(lambda: require_api_permission("profitcenter.delete"))])
async def delete_profit_center(profit_center_id: UUID, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    result = await db.execute(select(ProfitCenter).where(ProfitCenter.id == profit_center_id))
    db_pc = result.scalar_one_or_none()
    if not db_pc:
        raise HTTPException(status_code=404, detail="Profit center not found")
    await db.delete(db_pc)
    await db.commit()
    # Trigger event
    await event_bus.publish("profit_center.deleted", {"profit_center_id": str(profit_center_id)})
    return {"detail": "Profit center deleted"}

# --- Cost Center APIs ---
@router.get("/{company_id}/cost-centers", response_model=List[CostCenterResponse], summary="List cost centers for a company", dependencies=[Depends(require_roles("Admin", "Accountant", "Viewer")), Depends(get_current_user), Depends(lambda: require_api_permission("costcenter.read"))])
async def list_cost_centers(company_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CostCenter).where(CostCenter.company_id == company_id))
    ccs = result.scalars().all()
    return [CostCenterResponse(**cc.__dict__) for cc in ccs]

@router.post("/{company_id}/cost-centers", response_model=CostCenterResponse, summary="Create cost center for a company", dependencies=[Depends(require_roles("Admin")), Depends(get_current_user), Depends(lambda: require_api_permission("costcenter.create"))])
async def create_cost_center(company_id: UUID, cc: CostCenterCreate, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    cc_data = cc.dict()
    cc_data.pop('company_id', None)
    # Ensure all required fields are present
    required_fields = ['cost_center_code', 'cost_center_name', 'center_type', 'name']
    for field in required_fields:
        if field not in cc_data or cc_data[field] is None or (isinstance(cc_data[field], str) and not cc_data[field].strip()):
            raise HTTPException(status_code=422, detail=f"Missing required field: {field}")
    # Ensure center_type is passed as a string value (not Enum)
    if hasattr(cc_data['center_type'], 'value'):
        cc_data['center_type'] = cc_data['center_type'].value
    db_cc = CostCenter(company_id=company_id, **cc_data)
    db.add(db_cc)
    from sqlalchemy.exc import IntegrityError
    try:
        await db.commit()
        await db.refresh(db_cc)
    except IntegrityError as ie:
        await db.rollback()
        # Check for unique constraint violation on cost_center_code per company
        if 'uq_cost_center_code_per_company' in str(ie.orig) or 'unique constraint' in str(ie.orig):
            raise HTTPException(status_code=409, detail="A cost center with this code already exists for this company.")
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(ie)}")
    # Trigger event
    await event_bus.publish("cost_center.created", {"cost_center_id": str(db_cc.id), "company_id": str(company_id)})
    return CostCenterResponse(**db_cc.__dict__)

@router.get("/cost-centers/{cost_center_id}", response_model=CostCenterResponse, summary="Get cost center by ID", dependencies=[Depends(require_roles("Admin", "Accountant", "Viewer")), Depends(get_current_user), Depends(lambda: require_api_permission("costcenter.read"))])
async def get_cost_center(cost_center_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CostCenter).where(CostCenter.id == cost_center_id))
    cc = result.scalar_one_or_none()
    if not cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    return CostCenterResponse(**cc.__dict__)

@router.put("/cost-centers/{cost_center_id}", response_model=CostCenterResponse, summary="Update cost center", dependencies=[Depends(require_roles("Admin")), Depends(get_current_user), Depends(lambda: require_api_permission("costcenter.update"))])
async def update_cost_center(cost_center_id: UUID, cc: CostCenterUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CostCenter).where(CostCenter.id == cost_center_id))
    db_cc = result.scalar_one_or_none()
    if not db_cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    for k, v in cc.dict(exclude_unset=True).items():
        setattr(db_cc, k, v)
    await db.commit()
    await db.refresh(db_cc)
    return CostCenterResponse(**db_cc.__dict__)

@router.delete("/cost-centers/{cost_center_id}", summary="Delete cost center", dependencies=[Depends(require_roles("Admin")), Depends(get_current_user), Depends(lambda: require_api_permission("costcenter.delete"))])
async def delete_cost_center(cost_center_id: UUID, db: AsyncSession = Depends(get_db), event_bus: EventBus = Depends(get_event_bus)):
    result = await db.execute(select(CostCenter).where(CostCenter.id == cost_center_id))
    db_cc = result.scalar_one_or_none()
    if not db_cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    await db.delete(db_cc)
    await db.commit()
    # Trigger event
    await event_bus.publish("cost_center.deleted", {"cost_center_id": str(cost_center_id)})
    return {"detail": "Cost center deleted"}
