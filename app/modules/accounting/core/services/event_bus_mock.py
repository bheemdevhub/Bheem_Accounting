# Simple mock EventBus to replace missing bheem_core.event_bus
class EventBus:
    """Mock EventBus for development until bheem_core is properly installed"""
    
    def __init__(self):
        pass
    
    async def publish(self, event_type: str, data: dict, source_module: str = None):
        """Mock publish method - just logs the event"""
        print(f"EVENT: {event_type} from {source_module}: {data}")
        return True
