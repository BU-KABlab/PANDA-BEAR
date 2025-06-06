"""
Synchronous wrapper for the Scale class.
Provides easy-to-use synchronous methods that wrap the async Scale class.
"""
#import asyncio
#from sartorius import Scale as AsyncScale
#from sartorius.mock import Scale as MockScale
#import logging


#logger = logging.getLogger('sartorius')

class SyncScale:
    """Synchronous wrapper for the Sartorius scale."""
    
    def __init__(self, address=None, **kwargs):
        """Initialize with the same parameters as the async Scale."""
        self.address = address
        
        # Override the baudrate to 19200 for your scale
        kwargs['baudrate'] = 19200
        
        self.kwargs = kwargs
        self.scale = AsyncScale(address=address, **kwargs)
        self._loop = None
        
        
    def _get_event_loop(self):
        """Get or create an event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            # If no event loop exists in this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    def _run_coroutine(self, coroutine):
        """Run a coroutine in the event loop."""
        loop = self._get_event_loop()
        if loop.is_running():
            # Use a future if the loop is already running
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            return future.result()
        else:
            return loop.run_until_complete(coroutine)
    
    def get(self):
        """Get scale reading synchronously."""
        try:
            result = self._run_coroutine(self.scale.get())
            if 'mass' in result:
                return result['mass']
            return 0.0
        except Exception as e:
            logger.error(f"Error getting scale reading: {e}")
            raise OSError(f"Unable to get reading from scale: {e}")
    
    def tare(self):
        """Zero the scale synchronously."""
        return self._run_coroutine(self.scale.zero())
    
    def get_info(self):
        """Get scale info synchronously."""
        return self._run_coroutine(self.scale.get_info())
       
    def disconnect(self):
        """Disconnect from the scale synchronously."""
        if hasattr(self.scale, 'disconnect'):
            return self._run_coroutine(self.scale.disconnect())
        return None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

class MockSyncScale(SyncScale):
    """
    A synchronous wrapper for the MockScale class.
    
    This class provides synchronous methods that internally handle the
    asynchronous calls to the MockScale class, making it easier to use
    in synchronous contexts.
    """
    
    def __init__(self, port=None, **kwargs):
        """
        Initialize a new MockSyncScale instance.
        
        Args:
            port: The port where the scale is connected
            **kwargs: Additional keyword arguments to pass to the MockScale constructor
        """
        self.scale = MockScale(port, **kwargs)
        self._loop = None
        self.scale.info = {
            "model": "SIWADCP-1-",
            "serial": "37454321",
            "software": "00-37-09",
            "measurement": "net"
        }
        self.scale.get = lambda: {"stable": True, "units": "kg", "mass": 0.0}
        self.scale.zero = lambda: None
        self.scale.get_info = lambda: self.scale.info
    