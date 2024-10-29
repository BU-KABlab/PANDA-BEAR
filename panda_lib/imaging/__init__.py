"""
This module is used to capture images from the FLIR camera.
"""

# from .camera import FLIRCamera
from .camera_call_camera import capture_new_image, image_filepath_generator
from .image_tools import add_data_zone, invert_image
