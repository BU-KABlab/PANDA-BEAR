# panda_lib/hardware/imaging/flir_camera.py
try:
    import PySpin
    PYSPIN_AVAILABLE = True
except ImportError:
    PYSPIN_AVAILABLE = False

class FlirCamera:
    @staticmethod
    def is_available():
        return PYSPIN_AVAILABLE
        
    def __init__(self, *args, **kwargs):
        if not PYSPIN_AVAILABLE:
            raise ImportError("PySpin library is required for FLIR camera support")
        # Initialize FLIR camera