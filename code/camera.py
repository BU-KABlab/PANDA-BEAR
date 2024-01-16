import argparse
import logging
import sys
from config.config import PATH_TO_LOGS
import PyCapture2


class FLIRCamera:
    def __init__(self):
        self.camera = None
        self.bus = None
        self.num_cams = None
        self.uid = None
        self.camera_logger: logging.Logger = logging.getLogger("FLIRCamera")
        self.capturing = False

        # Set up logging
        self.camera_logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        self.camera_logger.addHandler(ch)

        ch = logging.FileHandler(PATH_TO_LOGS / "camera.log")
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        self.camera_logger.addHandler(ch)



    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        self.disconnect()

    def connect(self):
        """Connect to the first camera found on the bus"""
        # Ensure sufficient cameras are found
        self.bus = PyCapture2.BusManager()
        self.num_cams = self.bus.getNumOfCameras()
        self.camera_logger.debug("Number of cameras detected: %d", self.num_cams)
        if not self.num_cams:
            self.camera_logger.debug("Insufficient number of cameras. Exiting...")
            sys.exit()

        # Select camera on 0th index
        self.camera = PyCapture2.Camera()
        self.uid = self.bus.getCameraFromIndex(0)
        self.camera.connect(self.uid)
        self.print_camera_info()

        # Enable camera embedded timestamp
        self.enable_embedded_timestamp(True)

        self.camera_logger.debug("Starting image capture...")
        self.camera.startCapture()

    def disconnect(self):
        """Disconnect the camera"""
        # Disable camera embedded timestamp
        self.camera.stopCapture()
        self.enable_embedded_timestamp(False)
        self.camera.disconnect()

    def print_build_info(self):
        """Prints PyCapture2 Library Information"""
        lib_ver = PyCapture2.getLibraryVersion()
        self.camera_logger.debug(
            "PyCapture2 library version: %d %d %d %d",
            lib_ver[0],
            lib_ver[1],
            lib_ver[2],
            lib_ver[3],
        )
        self.camera_logger.debug()

    def print_camera_info(self):
        """Prints camera details"""
        cam_info = self.camera.getCameraInfo()
        self.camera_logger.debug("\n*** CAMERA INFORMATION ***\n")
        self.camera_logger.debug("Serial number - %d", cam_info.serialNumber)
        self.camera_logger.debug("Camera model - %s", cam_info.modelName)
        self.camera_logger.debug("Camera vendor - %s", cam_info.vendorName)
        self.camera_logger.debug("Sensor - %s", cam_info.sensorInfo)
        self.camera_logger.debug("Resolution - %s", cam_info.sensorResolution)
        self.camera_logger.debug("Firmware version - %s", cam_info.firmwareVersion)
        self.camera_logger.debug(
            "Firmware build time - %s", cam_info.firmwareBuildTime
        )

    def enable_embedded_timestamp(self, enable_timestamp):
        """Enables/Disables embedded timestamp"""
        embedded_info = self.camera.getEmbeddedImageInfo()
        if embedded_info.available.timestamp:
            self.camera.setEmbeddedImageInfo(timestamp=enable_timestamp)
            if enable_timestamp:
                self.camera_logger.debug("\nTimeStamp is enabled.\n")
            else:
                self.camera_logger.debug("\nTimeStamp is disabled.\n")

    def grab_images(
        self, num_images_to_grab, save=False, save_path=None, save_name=None
    ):
        """Grabs images from the camera"""
        prev_ts = None
        cam = self.camera
        image: PyCapture2.Image = None  
        for i in range(num_images_to_grab):
            try:
                image = cam.retrieveBuffer()
            except PyCapture2.Fc2error as fc2_err:
                self.camera_logger.debug("Error retrieving buffer : %s", fc2_err)
                continue

            ts = image.getTimeStamp()
            if prev_ts:
                diff = (ts.cycleSeconds - prev_ts.cycleSeconds) * 8000 + (
                    ts.cycleCount - prev_ts.cycleCount
                )
                self.camera_logger.debug(
                    "Timestamp [ %d %d ] - %d", ts.cycleSeconds, ts.cycleCount, diff
                )
            prev_ts = ts

        newimg = image.convert(PyCapture2.PIXEL_FORMAT.BGR)
        if save:
            if save_path is None:
                save_path = ""
            if save_name is None:
                save_name = "fc2TestImage.png"
            self.camera_logger.debug("Saving the last image to {0}".format(save_name))
            newimg.save(
                (save_path + save_name).encode("utf-8"),
                PyCapture2.IMAGE_FILE_FORMAT.PNG,
            )
        return newimg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some integers.")

    parser.add_argument(
        "--num_images", type=int, default=1, help="Number of images to grab"
    )
    parser.add_argument(
        "--save", type=bool, default=False, help="Whether to save the image"
    )
    parser.add_argument(
        "--file_name", type=str, default="", help="Name of the file to save"
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    with FLIRCamera() as camera:
        camera.grab_images(
            num_images_to_grab=int(args.num_images),
            save=True,
            save_path="images/",
            save_name=args.file_name,
        )
