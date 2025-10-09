class CameraInterface:
    """Abstract interface for camera operations"""

    def capture_image(self, *args, **kwargs):
        raise NotImplementedError

    def set_parameters(self, *args, **kwargs):
        raise NotImplementedError
