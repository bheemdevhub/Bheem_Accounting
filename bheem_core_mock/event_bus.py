"""Mock Event Bus for production deployment"""
import asyncio
from typing import Any, Dict, Optional

class EventBus:
    """Mock EventBus for production deployment"""
    
    def __init__(self):
        self.events = {}
    
    async def publish(self, event_type: str, data: Dict[str, Any], source_module: Optional[str] = None):
        """Mock publish method - logs event but doesn't actually process it"""
        print(f"[EventBus] Published event: {event_type} from {source_module}")
        return True
    
    async def subscribe(self, event_type: str, handler):
        """Mock subscribe method"""
        print(f"[EventBus] Subscribed to event: {event_type}")
        return True

# Create a global instance
event_bus = EventBus()
