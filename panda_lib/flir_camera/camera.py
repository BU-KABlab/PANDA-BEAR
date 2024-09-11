#!/c:/Users/Kab Lab/anaconda3/envs/python360/python.exe
"""
Requires the PyCapture2 library to be installed and run in a python 3.6 environment.
This script is used to capture images from the FLIR camera.
"""

import logging
from pathlib import Path
import os
from typing import Union
import PySpin
# from panda_lib.log_tools import setup_default_logger


# logger = setup_default_logger(
#     log_name="FLIRCamera", console_level=logging.DEBUG, file_level=logging.DEBUG
# )


def locate_connected_cameras() -> PySpin.CameraList:
    """
    This function locates all connected cameras and returns the list of cameras found.
    """

    # Retrieve singleton reference to system object
    system: PySpin.SystemPtr = PySpin.System.GetInstance()

    # Get current library version
    version: PySpin.LibraryVersion = system.GetLibraryVersion()
    print(f"Library version: {version.major}.{version.minor}.{version.type}.{version.build}")
    # Retrieve list of cameras from the system
    cam_list: PySpin.CameraList = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print(f"Number of cameras detected: {num_cameras}")

    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print("Not enough cameras!")
        input("Done! Press Enter to exit...")
        return False

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    input("Done! Press Enter to exit...")
    return cam_list

def fetch_camera_list() -> PySpin.CameraList:
    """
    This function locates all connected cameras and returns the list of cameras found.
    """

    # Retrieve singleton reference to system object
    system: PySpin.SystemPtr = PySpin.System.GetInstance()

    # Get current library version
    version: PySpin.LibraryVersion = system.GetLibraryVersion()
    print(f"Library version: {version.major}.{version.minor}.{version.type}.{version.build}")
    # Retrieve list of cameras from the system
    cam_list: PySpin.CameraList = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print(f"Number of cameras detected: {num_cameras}")

    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print("Not enough cameras!")
        input("Done! Press Enter to exit...")
        return False

    return cam_list

class StreamMode:
    """
    'Enum' for choosing stream mode
    """

    STREAM_MODE_TELEDYNE_GIGE_VISION = 0  # Teledyne Gige Vision stream mode is the default stream mode for spinview which is supported on Windows
    STREAM_MODE_PGRLWF = 1  # Light Weight Filter driver is our legacy driver which is supported on Windows
    STREAM_MODE_SOCKET = 2  # Socket is supported for MacOS and Linux, and uses native OS network sockets instead of a filter driver


CHOSEN_STREAMMODE = StreamMode.STREAM_MODE_TELEDYNE_GIGE_VISION
NUM_IMAGES = 10  # number of images to grab


def set_stream_mode(
    cam: PySpin.CameraPtr, stream_mode: StreamMode = CHOSEN_STREAMMODE
) -> bool:
    """
    This function changes the stream mode

    :param cam: Camera to change stream mode.
    :type cam: CameraPtr
    :type nodemap_tlstream: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    stream_mode = "TeledyneGigeVision"

    if stream_mode == StreamMode.STREAM_MODE_TELEDYNE_GIGE_VISION:
        stream_mode = "TeledyneGigeVision"
    elif stream_mode == StreamMode.STREAM_MODE_PGRLWF:
        stream_mode = "LWF"
    elif stream_mode == StreamMode.STREAM_MODE_SOCKET:
        stream_mode = "Socket"

    result = True

    # Retrieve Stream nodemap
    nodemap_tlstream = cam.GetTLStreamNodeMap()

    # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
    node_stream_mode = PySpin.CEnumerationPtr(nodemap_tlstream.GetNode("StreamMode"))

    # The node "StreamMode" is only available for GEV cameras.
    # Skip setting stream mode if the node is inaccessible.
    if not PySpin.IsReadable(node_stream_mode) or not PySpin.IsWritable(
        node_stream_mode
    ):
        return True

    # Retrieve the desired entry node from the enumeration node
    node_stream_mode_custom = PySpin.CEnumEntryPtr(
        node_stream_mode.GetEntryByName(stream_mode)
    )

    if not PySpin.IsReadable(node_stream_mode_custom):
        # Failed to get custom stream node
        print(f"Stream mode {stream_mode} not available. Aborting...")
        return False

    # Retrieve integer value from entry node
    stream_mode_custom = node_stream_mode_custom.GetValue()

    # Set integer as new value for enumeration node
    node_stream_mode.SetIntValue(stream_mode_custom)

    print(f"Stream Mode set to {node_stream_mode.GetCurrentEntry().GetSymbolic()}...")
    return result


def acquire_images(
    cam: PySpin.CameraPtr,
    nodemap: PySpin.INodeMap,
    nodemap_tldevice: PySpin.INodeMap,
    image_path: Union[str, Path] = None,
    num_images: int = NUM_IMAGES,
) -> bool:
    """
    This function acquires and saves 10 images from a device.

    :param cam: Camera to acquire images from.
    :param nodemap: Device nodemap.
    :param nodemap_tldevice: Transport layer device nodemap.
    :type cam: CameraPtr
    :type nodemap: INodeMap
    :type nodemap_tldevice: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    print("*** IMAGE ACQUISITION ***\n")
    try:
        result = True

        # Set acquisition mode to continuous
        #
        #  *** NOTES ***
        #  Because the example acquires and saves 10 images, setting acquisition
        #  mode to continuous lets the example finish. If set to single frame
        #  or multiframe (at a lower number of images), the example would just
        #  hang. This would happen because the example has been written to
        #  acquire 10 images while the camera would have been programmed to
        #  retrieve less than that.
        #
        #  Setting the value of an enumeration node is slightly more complicated
        #  than other node types. Two nodes must be retrieved: first, the
        #  enumeration node is retrieved from the nodemap; and second, the entry
        #  node is retrieved from the enumeration node. The integer value of the
        #  entry node is then set as the new value of the enumeration node.
        #
        #  Notice that both the enumeration and the entry nodes are checked for
        #  availability and readability/writability. Enumeration nodes are
        #  generally readable and writable whereas their entry nodes are only
        #  ever readable.
        #
        #  Retrieve enumeration node from nodemap

        # In order to access the node entries, they have to be casted to a 
        # pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(
            nodemap.GetNode("AcquisitionMode")
        )
        if not PySpin.IsReadable(node_acquisition_mode) or not PySpin.IsWritable(
            node_acquisition_mode
        ):
            print(
                "Unable to set acquisition mode to continuous (enum retrieval). Aborting..."
            )
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(
            "Continuous"
        )
        if not PySpin.IsReadable(node_acquisition_mode_continuous):
            print(
                "Unable to set acquisition mode to continuous (entry retrieval). Aborting..."
            )
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        print("Acquisition mode set to continuous...")

        #  Begin acquiring images
        #
        #  *** NOTES ***
        #  What happens when the camera begins acquiring images depends on the
        #  acquisition mode. Single frame captures only a single image, multi
        #  frame catures a set number of images, and continuous captures a
        #  continuous stream of images. Because the example calls for the
        #  retrieval of 10 images, continuous mode has been set.
        #
        #  *** LATER ***
        #  Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()

        print("Acquiring images...")

        #  Retrieve device serial number for filename
        #
        #  *** NOTES ***
        #  The device serial number is retrieved in order to keep cameras from
        #  overwriting one another. Grabbing image IDs could also accomplish
        #  this.
        device_serial_number = ""
        node_device_serial_number = PySpin.CStringPtr(
            nodemap_tldevice.GetNode("DeviceSerialNumber")
        )
        if PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print(f"Device serial number retrieved as {device_serial_number}...")

        # Retrieve, convert, and save images

        # Create ImageProcessor instance for post processing images
        processor = PySpin.ImageProcessor()

        # Set default image processor color processing method
        #
        # *** NOTES ***
        # By default, if no specific color processing algorithm is set, the image
        # processor will default to NEAREST_NEIGHBOR method.
        processor.SetColorProcessing(
            PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR
        )

        for i in range(num_images):
            try:

                #  Retrieve next received image
                #
                #  *** NOTES ***
                #  Capturing an image houses images on the camera buffer. Trying
                #  to capture an image that does not exist will hang the camera.
                #
                #  *** LATER ***
                #  Once an image from the buffer is saved and/or no longer
                #  needed, the image must be released in order to keep the
                #  buffer from filling up.
                image_result: PySpin.ImagePtr = cam.GetNextImage(1000)

                #  Ensure image completion
                #
                #  *** NOTES ***
                #  Images can easily be checked for completion. This should be
                #  done whenever a complete image is expected or required.
                #  Further, check image status for a little more insight into
                #  why an image is incomplete.
                if image_result.IsIncomplete():
                    print(
                        f"Image incomplete with image status {image_result.GetImageStatus()}..."
                    )

                else:

                    #  Print image information; height and width recorded in pixels
                    #
                    #  *** NOTES ***
                    #  Images have quite a bit of available metadata including
                    #  things such as CRC, image status, and offset values, to
                    #  name a few.
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    print(f"Grabbed Image {i}, width = {width}, height = {height}...")

                    #  Convert image to mono 8
                    #
                    #  *** NOTES ***
                    #  Images can be converted between pixel formats by using
                    #  the appropriate enumeration value. Unlike the original
                    #  image, the converted one does not need to be released as
                    #  it does not affect the camera buffer.
                    #
                    #  When converting images, color processing algorithm is an
                    #  optional parameter.
                    # image_converted: PySpin.ImagePtr = processor.Convert(
                    #     image_result, PySpin.PixelFormat_BayerBG8
                    # )

                    # Create a unique filename
                    if device_serial_number:
                        filename = f"Acquisition-{device_serial_number}-{i}.jpg"
                    else:  # if serial number is empty
                        filename = f"Acquisition-{i}.jpg"

                    #  Save image
                    #
                    #  *** NOTES ***
                    #  The standard practice of the examples is to use device
                    #  serial numbers to keep images of one device from
                    #  overwriting those of another.
                    if image_path is None:
                        image_path = Path("images")
                        filepath = os.path.join(image_path, filename)
                    else:
                        image_path = Path(image_path)
                        filepath = image_path
                    # image_converted.Save(filepath)
                    image_result.Save(filepath)
                    print(f"Image saved at {filepath}...")

                    #  Release image
                    #
                    #  *** NOTES ***
                    #  Images retrieved directly from the camera (i.e. non-converted
                    #  images) need to be released in order to keep from filling the
                    #  buffer.
                    image_result.Release()
                    print("")

            except PySpin.SpinnakerException as ex:
                print(f"Error: {ex}")
                return False

        #  End acquisition
        #
        #  *** NOTES ***
        #  Ending acquisition appropriately helps ensure that devices clean up
        #  properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print(f"Error: {ex}")
        return False

    return result


def print_device_info(nodemap: PySpin.INodeMap) -> bool:
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    print("*** DEVICE INFORMATION ***\n")

    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(
            nodemap.GetNode("DeviceInformation")
        )

        if PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print(
                    f"{node_feature.GetName()}: {node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'}"
                )

        else:
            print("Device control information not readable.")

    except PySpin.SpinnakerException as ex:
        print(f"Error: {ex}")
        return False

    return result


def run_single_camera(cam: PySpin.CameraPtr, image_path: Union[str, Path] = None, num_images:int = 1) -> bool:
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        result &= print_device_info(nodemap_tldevice)

        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Set Stream Modes
        # result &= set_stream_mode(cam)

        # Acquire images
        result &= acquire_images(cam, nodemap, nodemap_tldevice, image_path, num_images)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print(f"Error: {ex}")
        result = False

    return 0


if __name__ == "__main__":
    # This function locates all connected cameras
    locate_connected_cameras()
    system = PySpin.System.GetInstance()
    camera_list = system.GetCameras()
    pyspin_system: PySpin.SystemPtr = PySpin.System.GetInstance()
    # Run example on each camera
    for instance, camera in enumerate(camera_list):
        print(f"Running example for camera {instance+1}...")
        RESULT = run_single_camera(camera)
        if RESULT:
            print(f"Camera {instance+1} example complete...")
        else:
            print(f"Camera {instance+1} example failed...")
    # Clear camera list before releasing system
    camera_list.Clear()

    # Release system instance
    pyspin_system.ReleaseInstance()

    input("Done! Press Enter to exit...")
