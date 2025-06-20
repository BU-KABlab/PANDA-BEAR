# panda_lib/hardware/imaging/flir_camera.py
"""
FLIR camera implementation using PySpin.
This module provides a wrapper around the PySpin library for FLIR cameras.
Due to Python versioning issues, it uses `simple_pyspin` as a drop-in replacement for PySpin.
"""

import simple_pyspin as PySpin
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from .interface import CameraInterface
from .flir_camera_tools import file_enumeration
#from .flir_camera_tools import file_enumeration, run_single_camera

# Try to import PySpin, but make it optional
#try:
    # import PySpin # PySpin only works with Python <=3.10
#    import simple_pyspin as PySpin
#    PYSPIN_AVAILABLE = True
#except ImportError:
#    PYSPIN_AVAILABLE = False


class FlirCamera(CameraInterface):
    """
    Implementation of CameraInterface for FLIR cameras using PySpin
    """
    
    @staticmethod
    def is_available() -> bool:
        """Check if PySpin is available
        
        Returns:
            bool: True if PySpin is available, False otherwise
        """
        return PYSPIN_AVAILABLE
    
    def __init__(self, camera_id: int = 0):
        """Initialize FLIR camera
        
        Args:
            camera_id: The ID of the camera to use
            
        Raises:
            ImportError: If PySpin is not available
        """
        if not PYSPIN_AVAILABLE:
            raise ImportError("simple-pyspin is required for FLIR camera support")
        
        self.camera_id = camera_id
        self.logger = logging.getLogger("panda.flir_camera")
        self.cam = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to the FLIR camera
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("simple-pyspin not available")
            return False
        
        try:
            cam_list = PySpin.list_cameras()
            
            if len(cam_list) == 0:
                self.logger.error("No FLIR cameras found")
                return False
            
            # Get the specified camera (or first one if index out of range)
            if self.camera_id < len(cam_list):
                self.cam = cam_list[self.camera_id]
            else:
                self.logger.warning(f"Camera ID {self.camera_id} out of range, using first camera")
                self.cam = cam_list[0]
            
            # Initialize the camera
            self.cam.init()
            self.connected = True
            self.logger.info(f"Connected to FLIR camera ID {self.camera_id}")
            return True
            
        except Exception as ex:
            self.logger.error(f"Error connecting to FLIR camera: {ex}")
            return False
    
    def close(self) -> None:
        """Disconnect from the FLIR camera"""
        if not PYSPIN_AVAILABLE or not self.connected:
            return
        
        try:
            if self.cam is not None:
                self.cam.close()
                self.cam = None
            
            self.connected = False
            self.logger.info("Disconnected from FLIR camera")
            
        except Exception as ex:
            self.logger.error(f"Error disconnecting from FLIR camera: {ex}")
    
    def is_connected(self) -> bool:
        """Check if the FLIR camera is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected and self.cam is not None
    
    def capture_image(self) -> Optional['PySpin.Image']:
        """Capture a single image from the FLIR camera
        
        Returns:
            PySpin.ImagePtr: The captured image, or None if capturing failed
        """
        if not PYSPIN_AVAILABLE or not self.is_connected():
            self.logger.error("Cannot capture image: Camera not connected")
            return None
        
        try:
            # Begin acquisition
            self.cam.start()
            
            # Get the image
            image = self.cam.get_image()
            
            # End acquisition
            self.cam.stop()
            
            return image
            
        except Exception as ex:
            self.logger.error(f"Error capturing image from FLIR camera: {ex}")
            return None
    
    def save_image(self, image: 'PySpin.Image', path: Union[str, Path]) -> bool:
        """Save an image to disk
        
        Args:
            image: The image to save
            path: The path to save the image to
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("simple-pyspin not available")
            return False
        
        try:
            path = Path(path) if isinstance(path, str) else path
            
            # Make sure the directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the image
            image.save(str(path))
            
            # Release the image
            image.release()
            
            self.logger.info(f"Image saved to {path}")
            return True
            
        except Exception as ex:
            self.logger.error(f"Error saving image from FLIR camera: {ex}")
            return False
    
    def capture_and_save(self, path: Union[str, Path]) -> Tuple[Path, bool]:
        """Capture an image and save it to disk
        
        Args:
            path: The path to save the image to
            
        Returns:
            Tuple[Path, bool]: The path of the saved image and a boolean indicating success
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("simple-pyspin not available")
            return Path(path), False
        
        path = Path(path) if isinstance(path, str) else path
        
        # Check the file name and enumerate if it already exists
        path = file_enumeration(path)
        
        if not self.is_connected():
            self.logger.error("Cannot capture image: Camera not connected")
            return path, False
        
        image = self.capture_image()
        if image is not None:
            success = self.save_image(image, path)
            return path, success
        else:
            return path, False
