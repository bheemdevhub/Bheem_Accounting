# Local stub for bheem_core when not available
# This provides fallback functionality for deployment environments

from typing import Any, Dict, Optional
from enum import Enum
import asyncio


class EventBus:
    """Simple event bus stub for when bheem_core is not available"""
    
    async def publish(self, event_name: str, data: Dict[str, Any], source_module: str = None):
        """Stub method that does nothing - no-op event publishing"""
        pass


# Mock database connection
async def get_mock_db():
    """Mock database connection for when bheem_core is not available"""
    yield None


# Mock user role enum
class UserRole(str, Enum):
    """Mock UserRole enum"""
    ADMIN = "admin"
    USER = "user"
    MANAGER = "manager"


# Mock models that might be imported
class Company:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Currency:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# Mock enums
class ProfitCenterType(str, Enum):
    STANDARD = "standard"
    INVESTMENT = "investment"


class BudgetType(str, Enum):
    OPERATIONAL = "operational"
    CAPITAL = "capital"


class AllocationMethod(str, Enum):
    DIRECT = "direct"
    PROPORTIONAL = "proportional"


class VarianceType(str, Enum):
    FAVORABLE = "favorable"
    UNFAVORABLE = "unfavorable"


class SignificanceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Mock base module class
class BaseERPModule:
    def __init__(self, name: str):
        self.name = name
    
    def get_routes(self):
        return []


# Create a mock event bus instance
event_bus = EventBus()


# Mock database get function
def get_db():
    return get_mock_db()
