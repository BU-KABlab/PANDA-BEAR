"""
Interface for camera classes to implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Union


class CameraInterface(ABC):
    """
    Abstract base class that defines the interface for camera implementations.
    Both OpenCVCamera and FlirCamera should implement this interface.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the camera.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Disconnect from the camera.
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the camera is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def capture_image(self):
        """
        Capture a single image.
        
        Returns:
            Image data in the format specific to the camera implementation
        """
        pass
    
    @abstractmethod
    def save_image(self, image, path: Union[str, Path]) -> bool:
        """
        Save an image to disk.
        
        Args:
            image: The image to save
            path: The path to save the image to
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def capture_and_save(self, path: Union[str, Path]) -> Tuple[Path, bool]:
        """
        Capture an image and save it to disk.
        
        Args:
            path: The path to save the image to
            
        Returns:
            Tuple[Path, bool]: The path of the saved image and a boolean indicating success
        """
        pass