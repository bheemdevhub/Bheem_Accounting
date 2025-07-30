# app/modules/accounting/api/v1/routes/journal_entries.py
"""Journal entries routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from bheem_core.modules.accounting.core.schemas.accounting_schemas import JournalEntryCreate, JournalEntryResponse, JournalEntryListResponse, JournalEntryUpdate, JournalEntryLineCreate, JournalEntryLineResponse
from bheem_core.modules.accounting.core.services.accounting_service import JournalEntryService
from bheem_core.core.database import get_db
from bheem_core.modules.auth.core.services.permissions_service import require_roles, require_api_permission, get_current_user
from functools import partial
from bheem_core.core.event_bus import EventBus
from bheem_core.modules.accounting.config import AccountingEventTypes
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func

router = APIRouter(prefix="/journal-entries", tags=["Journal Entries"])

def get_journal_entry_service(db: AsyncSession = Depends(get_db)):
    # Pass event bus to service for event publishing
    return JournalEntryService(db, event_bus=EventBus())

# Helper for permission dependency
def permission_dep(permission_code: str):
    # Returns a dependency callable for the given permission code
    return Depends(partial(require_api_permission, permission_code=permission_code))

@router.get("/", response_model=JournalEntryListResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), permission_dep("accounting.view_journal_entry")])
async def list_journal_entries(skip: int = 0, limit: int = 100, service: JournalEntryService = Depends(get_journal_entry_service)):
    # Use selectinload to eagerly load lines to avoid async context errors
    from bheem_core.modules.accounting.core.models.accounting_models import JournalEntry
    from sqlalchemy.future import select
    db = service.db
    result = await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.lines)).order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit)
    )
    entries = result.scalars().all()
    return JournalEntryListResponse(journal_entries=entries)

@router.post("/", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin")), permission_dep("accounting.create_journal_entry")])
async def create_journal_entry(entry: JournalEntryCreate, service: JournalEntryService = Depends(get_journal_entry_service)):
    from sqlalchemy.exc import IntegrityError
    # Auto-generate entry_number if not provided
    if not getattr(entry, "entry_number", None):
        # Generate entry_number in format: JE-YYYYMMDD-XXX (incremental per day per company)
        from datetime import datetime
        today = entry.entry_date if hasattr(entry, "entry_date") and entry.entry_date else datetime.utcnow().date()
        company_id = entry.company_id
        db = service.db
        from sqlalchemy import func
        from bheem_core.modules.accounting.core.models.accounting_models import JournalEntry
        # Count existing entries for today and company
        result = await db.execute(
            select(func.count()).select_from(JournalEntry).where(
                JournalEntry.company_id == company_id,
                JournalEntry.entry_date == today
            )
        )
        count = result.scalar() or 0
        next_number = count + 1
        entry_number = f"JE-{today.strftime('%Y%m%d')}-{next_number:03d}"
        entry.entry_number = entry_number
    try:
        created = await service.create_journal_entry(entry)
    except IntegrityError as ie:
        if 'uq_entry_number_per_company' in str(ie.orig) or 'unique constraint' in str(ie.orig):
            raise HTTPException(status_code=409, detail="A journal entry with this entry number already exists for this company.")
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(ie)}")
    # Publish event after creation
    await service.event_bus.publish(AccountingEventTypes.JOURNAL_ENTRY_POSTED, {"entry_id": str(created.id)})
    return created

@router.get("/{entry_id}", response_model=JournalEntryResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), permission_dep("accounting.view_journal_entry")])
async def get_journal_entry(entry_id: UUID, service: JournalEntryService = Depends(get_journal_entry_service)):
    # Eagerly load lines to avoid async lazy-load error
    entry = await service.get_journal_entry_with_lines(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry

@router.put("/{entry_id}", response_model=JournalEntryResponse, dependencies=[Depends(require_roles("Accountant", "Admin")), permission_dep("accounting.update_journal_entry")])
async def update_journal_entry(entry_id: UUID, entry: JournalEntryUpdate, service: JournalEntryService = Depends(get_journal_entry_service)):
    updated = await service.update_journal_entry_with_lines(entry_id, entry)
    if not updated:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return updated

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), permission_dep("accounting.delete_journal_entry")])
async def delete_journal_entry(entry_id: UUID, service: JournalEntryService = Depends(get_journal_entry_service)):
    deleted = await service.delete_journal_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return None

@router.get("/lines/{line_id}", response_model=JournalEntryLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin", "Viewer")), permission_dep("accounting.view_journal_entry")])
async def get_journal_entry_line(line_id: UUID, service: JournalEntryService = Depends(get_journal_entry_service)):
    line = await service.get_journal_entry_line(line_id)
    if not line:
        raise HTTPException(status_code=404, detail="Journal entry line not found")
    return line

@router.post("/lines/", response_model=JournalEntryLineResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Accountant", "Admin")), permission_dep("accounting.create_journal_entry")])
async def create_journal_entry_line(line: JournalEntryLineCreate, service: JournalEntryService = Depends(get_journal_entry_service)):
    created = await service.create_journal_entry_line(line)
    # Publish event for line creation
    await service.event_bus.publish(AccountingEventTypes.JOURNAL_ENTRY_LINE_CREATED, {"line_id": str(created.id), "journal_entry_id": str(created.journal_entry_id)})
    return created

@router.put("/lines/{line_id}", response_model=JournalEntryLineResponse, dependencies=[Depends(require_roles("Accountant", "Admin")), permission_dep("accounting.update_journal_entry")])
async def update_journal_entry_line(line_id: UUID, line: JournalEntryLineCreate, service: JournalEntryService = Depends(get_journal_entry_service)):
    updated = await service.update_journal_entry_line(line_id, line)
    if not updated:
        raise HTTPException(status_code=404, detail="Journal entry line not found")
    # Publish event for line update
    await service.event_bus.publish(AccountingEventTypes.JOURNAL_ENTRY_LINE_UPDATED, {"line_id": str(line_id), "journal_entry_id": str(updated.journal_entry_id)})
    return updated

@router.delete("/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin")), permission_dep("accounting.delete_journal_entry")])
async def delete_journal_entry_line(line_id: UUID, service: JournalEntryService = Depends(get_journal_entry_service)):
    deleted = await service.delete_journal_entry_line(line_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Journal entry line not found")
    # Publish event for line deletion
    await service.event_bus.publish(AccountingEventTypes.JOURNAL_ENTRY_LINE_DELETED, {"line_id": str(line_id)})
    return None

