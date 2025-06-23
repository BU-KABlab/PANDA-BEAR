# panda_lib/hardware/imaging/flir_camera.py
"""
FLIR camera implementation using PySpin.
This module provides a wrapper around the PySpin library for FLIR cameras.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from .interface import CameraInterface
from .flir_camera_tools import file_enumeration, run_single_camera

# Try to import PySpin, but make it optional
try:
    import PySpin # PySpin only works with Python <=3.10
    
    PYSPIN_AVAILABLE = True
except ImportError:
    PYSPIN_AVAILABLE = False


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
            raise ImportError("PySpin library is required for FLIR camera support")
        
        self.camera_id = camera_id
        self.logger = logging.getLogger("panda.flir_camera")
        self.system = None
        self.camera_list = None
        self.camera = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to the FLIR camera
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("PySpin library not available")
            return False
        
        try:
            # Initialize PySpin system
            self.system = PySpin.System.GetInstance()
            self.camera_list = self.system.GetCameras()
            
            if self.camera_list.GetSize() == 0:
                self.logger.error("No FLIR cameras found")
                return False
            
            # Get the specified camera (or first one if index out of range)
            if self.camera_id < self.camera_list.GetSize():
                self.camera = self.camera_list[self.camera_id]
            else:
                self.logger.warning(f"Camera ID {self.camera_id} out of range, using first camera")
                self.camera = self.camera_list[0]
            
            # Initialize the camera
            self.camera.Init()
            self.connected = True
            self.logger.info(f"Connected to FLIR camera ID {self.camera_id}")
            return True
            
        except PySpin.SpinnakerException as ex:
            self.logger.error(f"Error connecting to FLIR camera: {ex}")
            return False
    
    def close(self) -> None:
        """Disconnect from the FLIR camera"""
        if not PYSPIN_AVAILABLE or not self.connected:
            return
        
        try:
            if self.camera is not None:
                self.camera.DeInit()
                self.camera = None
            
            if self.camera_list is not None:
                self.camera_list.Clear()
                self.camera_list = None
            
            if self.system is not None:
                self.system.ReleaseInstance()
                self.system = None
            
            self.connected = False
            self.logger.info("Disconnected from FLIR camera")
            
        except PySpin.SpinnakerException as ex:
            self.logger.error(f"Error disconnecting from FLIR camera: {ex}")
    
    def is_connected(self) -> bool:
        """Check if the FLIR camera is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected and self.camera is not None
    
    def capture_image(self) -> Optional[PySpin.ImagePtr]:
        """Capture a single image from the FLIR camera
        
        Returns:
            PySpin.ImagePtr: The captured image, or None if capturing failed
        """
        if not PYSPIN_AVAILABLE or not self.is_connected():
            self.logger.error("Cannot capture image: Camera not connected")
            return None
        
        try:
            # Begin acquisition
            self.camera.BeginAcquisition()
            
            # Get the image
            image_result = self.camera.GetNextImage(1000)
            
            # Check if the image is complete
            if image_result.IsIncomplete():
                self.logger.error(f"Image incomplete with status {image_result.GetImageStatus()}")
                image_result.Release()
                self.camera.EndAcquisition()
                return None
            
            # End acquisition
            self.camera.EndAcquisition()
            
            return image_result
            
        except PySpin.SpinnakerException as ex:
            self.logger.error(f"Error capturing image from FLIR camera: {ex}")
            self.camera.EndAcquisition()
            return None
    
    def save_image(self, image: PySpin.ImagePtr, path: Union[str, Path]) -> bool:
        """Save an image to disk
        
        Args:
            image: The image to save
            path: The path to save the image to
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("PySpin library not available")
            return False
        
        try:
            path = Path(path) if isinstance(path, str) else path
            
            # Make sure the directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert the image to RGB8
            processor = PySpin.ImageProcessor()
            image_converted = processor.Convert(image, PySpin.PixelFormat_RGB8)
            
            # Save the image
            image_converted.Save(str(path))
            
            # Release the image
            image.Release()
            
            self.logger.info(f"Image saved to {path}")
            return True
            
        except PySpin.SpinnakerException as ex:
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
            self.logger.error("PySpin library not available")
            return Path(path), False
        
        path = Path(path) if isinstance(path, str) else path
        
        # Check the file name and enumerate if it already exists
        path = file_enumeration(path)
        
        try:
            # Instead of using our own implementation, use the existing run_single_camera function
            if self.is_connected():
                result = run_single_camera(self.camera, image_path=path, num_images=1)
                return path, result
            else:
                self.logger.error("Cannot capture image: Camera not connected")
                return path, False
        except Exception as e:
            self.logger.error(f"Error in capture_and_save: {e}")
            return path, False
