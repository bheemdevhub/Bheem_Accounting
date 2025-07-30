from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID

class AccountResponse(BaseModel):
    id: UUID
    company_id: UUID
    account_code: str
    account_name: str
    account_category: str
    account_type: str
    parent_account_id: Optional[UUID] = None
    is_control_account: Optional[bool] = None
    is_inter_company: Optional[bool] = None
    cost_center_required: Optional[bool] = None
    sku_tracking_enabled: Optional[bool] = None
    consolidation_account_id: Optional[UUID] = None
    elimination_account: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

