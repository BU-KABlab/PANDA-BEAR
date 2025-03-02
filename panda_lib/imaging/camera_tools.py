"""
Requires the PySpin library to be installed and run in a python <=3.10 environment.
This script is used to capture images from the FLIR camera.
"""

import logging
import os
from pathlib import Path
from typing import Union

import PySpin

from shared_utilities.log_tools import setup_default_logger

logger = setup_default_logger(
    log_file="FLIRCamera.log",
    log_name="camera",
    console_level=logging.ERROR,
    file_level=logging.DEBUG,
)


def file_enumeration(file_path: Path) -> Path:
    """Enumerate a file path if it already exists"""
    i = 1
    while file_path.exists():
        file_path = file_path.with_name(
            file_path.stem + "_" + str(i) + file_path.suffix
        )
        i += 1
    return file_path


def image_filepath_generator(
    exp_id: int = "test",
    project_id: int = "test",
    project_campaign_id: int = "test",
    well_id: str = "test",
    step_description: str = None,
    data_path: Path = Path("images"),
) -> Path:
    """
    Generate the file path for the image
    """
    # create file name
    if step_description is not None:
        file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_{step_description}_image"
    else:
        file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_image"
    file_name = file_name.replace(" ", "_")  # clean up the file name
    file_name_start = file_name + "_0"  # enumerate the file name
    filepath = Path(data_path / str(file_name_start)).with_suffix(".tiff")
    # i = 1
    while filepath.exists():
        filepath = file_enumeration(filepath)
    return filepath


def locate_connected_cameras() -> PySpin.CameraList:
    """
    This function locates all connected cameras and returns the list of cameras found.
    """

    # Retrieve singleton reference to system object
    system: PySpin.SystemPtr = PySpin.System.GetInstance()

    # Get current library version
    version: PySpin.LibraryVersion = system.GetLibraryVersion()
    print(
        f"Library version: {version.major}.{version.minor}.{version.type}.{version.build}"
    )
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
    print(
        f"Library version: {version.major}.{version.minor}.{version.type}.{version.build}"
    )
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

    # print("*** IMAGE ACQUISITION ***\n")
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

        # cam.Color
        # In order to access the node entries, they have to be casted to a
        # pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(
            nodemap.GetNode("AcquisitionMode")
        )
        if not PySpin.IsReadable(node_acquisition_mode) or not PySpin.IsWritable(
            node_acquisition_mode
        ):
            logger.error(
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

        logger.info("Acquisition mode set to continuous...")

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

        logger.info("Acquiring images...")

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
            logger.info("Device serial number retrieved as %s", device_serial_number)

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
                    msg = f"Image incomplete with image status {image_result.GetImageStatus()}..."
                    logger.error(msg)
                    raise PySpin.SpinnakerException(msg)

                else:
                    #  Print image information; height and width recorded in pixels
                    #
                    #  *** NOTES ***
                    #  Images have quite a bit of available metadata including
                    #  things such as CRC, image status, and offset values, to
                    #  name a few.
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    logger.info(
                        "Grabbed Image %s, width = %s, height = %s...", i, width, height
                    )
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
                    image_converted: PySpin.ImagePtr = processor.Convert(
                        image_result, PySpin.PixelFormat_RGB8
                    )

                    # Create a unique filename
                    if device_serial_number:
                        filename = f"Acquisition-{device_serial_number}-{i}.tiff"
                    else:  # if serial number is empty
                        filename = f"Acquisition-{i}.tiff"

                    #  Save image
                    #
                    #  *** NOTES ***
                    #  The standard practice of the examples is to use device
                    #  serial numbers to keep images of one device from
                    #  overwriting those of another.
                    if image_path is None:
                        image_path = Path("images")
                        filepath: Path = Path(os.path.join(image_path, filename))
                    else:
                        image_path = Path(image_path)
                        filepath: Path = image_path

                    raw_path = filepath.with_stem(f"{filepath.stem}_raw")
                    converted_path = filepath.with_stem(f"{image_path.stem}")

                    # cv2.imwrite(str(converted_path), image_converted)
                    try:
                        image_result.Save(str(raw_path))
                        image_converted.Save(str(converted_path))
                        logger.info("Image saved at %s...", filepath)
                    except PySpin.SpinnakerException as ex:
                        logger.error(f"Error: {ex}")
                        # If error try and save in the local directory as to not loose the image
                        image_result.Save(f"{filename}")

                    #  Release image
                    #
                    #  *** NOTES ***
                    #  Images retrieved directly from the camera (i.e. non-converted
                    #  images) need to be released in order to keep from filling the
                    #  buffer.
                    # image_result.Release()

            except PySpin.SpinnakerException as ex:
                print(f"Error: {ex}")
                return False

            finally:
                if image_result.IsIncomplete():
                    logger.error(
                        "Image incomplete with image status %s...",
                        image_result.GetImageStatus(),
                    )
                    image_result.Release()
                else:
                    logger.info("Image grabbed successfully...")
                    image_result.Release()

        #  End acquisition
        #
        #  *** NOTES ***
        #  Ending acquisition appropriately helps ensure that devices clean up
        #  properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()
        return result

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


def check_device_is_readable(nodemap: PySpin.INodeMap) -> bool:
    """This performs the same check as print_device_info without printing the information"""
    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(
            nodemap.GetNode("DeviceInformation")
        )

        if PySpin.IsReadable(node_device_information):
            result = True

        else:
            result = False

    except PySpin.SpinnakerException as ex:
        print(f"Error: {ex}")
        result = False

    return result


def run_single_camera(
    cam: PySpin.CameraPtr, image_path: Union[str, Path] = None, num_images: int = 1
) -> bool:
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

        result = check_device_is_readable(nodemap_tldevice)
        if not result:
            return False

        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Set Stream Modes
        # result &= set_stream_mode(cam)

        # Acquire images
        result = acquire_images(cam, nodemap, nodemap_tldevice, image_path, num_images)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print(f"Error: {ex}")
        result = False

    return result


def set_brightness(cam: PySpin.CameraPtr, brightness: int):
    """
    Sets the brightness for the camera.

    :param cam: Camera to set brightness for.
    :param brightness: Brightness value to set.
    :type cam: CameraPtr
    :type brightness: int
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("Brightness"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(brightness)
    #         print(f"Brightness set to: {brightness}")
    #     else:
    #         print("Brightness property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting brightness: {ex}")

    try:
        result = True
        cam.Brightness.SetValue(brightness)
        print(f"Brightness set to: {brightness}")
    except PySpin.SpinnakerException as ex:
        print(f"Error setting brightness: {ex}")
        result = False

    return result


def set_exposure(cam: PySpin.CameraPtr, exposure: float):
    """
    This function configures a custom exposure time. Automatic exposure is turned
    off in order to allow for the customization, and then the custom setting is
    applied.

    :param cam: Camera to configure exposure for.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    print("*** CONFIGURING EXPOSURE ***\n")

    try:
        result = True

        # Turn off automatic exposure mode
        #
        # *** NOTES ***
        # Automatic exposure prevents the manual configuration of exposure
        # times and needs to be turned off for this example. Enumerations
        # representing entry nodes have been added to QuickSpin. This allows
        # for the much easier setting of enumeration nodes to new values.
        #
        # The naming convention of QuickSpin enums is the name of the
        # enumeration node followed by an underscore and the symbolic of
        # the entry node. Selecting "Off" on the "ExposureAuto" node is
        # thus named "ExposureAuto_Off".
        #
        # *** LATER ***
        # Exposure time can be set automatically or manually as needed. This
        # example turns automatic exposure off to set it manually and back
        # on to return the camera to its default state.

        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print("Unable to disable automatic exposure. Aborting...")
            return False

        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        print("Automatic exposure disabled...")

        # Set exposure time manually; exposure time recorded in microseconds
        #
        # *** NOTES ***
        # Notice that the node is checked for availability and writability
        # prior to the setting of the node. In QuickSpin, availability and
        # writability are ensured by checking the access mode.
        #
        # Further, it is ensured that the desired exposure time does not exceed
        # the maximum. Exposure time is counted in microseconds - this can be
        # found out either by retrieving the unit with the GetUnit() method or
        # by checking SpinView.

        if cam.ExposureTime.GetAccessMode() != PySpin.RW:
            print("Unable to set exposure time. Aborting...")
            return False

        # Ensure desired exposure time does not exceed the maximum
        exposure_time_to_set = exposure
        exposure_time_to_set = min(cam.ExposureTime.GetMax(), exposure_time_to_set)
        cam.ExposureTime.SetValue(exposure_time_to_set)
        print("Shutter time set to %s us...\n" % exposure_time_to_set)

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        result = False

    return result


def reset_exposure(cam: PySpin.CameraPtr) -> bool:
    """
    This function returns the camera to a normal state by re-enabling automatic exposure.

    :param cam: Camera to reset exposure on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Turn automatic exposure back on
        #
        # *** NOTES ***
        # Automatic exposure is turned on in order to return the camera to its
        # default state.

        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print(
                "Unable to enable automatic exposure (node retrieval). Non-fatal error..."
            )
            return False

        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)

        print("Automatic exposure enabled...")

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        result = False

    return result


def set_sharpness(cam: PySpin.CameraPtr, sharpness: int):
    """
    Sets the sharpness for the camera.

    :param cam: Camera to set sharpness for.
    :param sharpness: Sharpness value to set.
    :type cam: CameraPtr
    :type sharpness: int
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("Sharpness"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(sharpness)
    #         print(f"Sharpness set to: {sharpness}")
    #     else:
    #         print("Sharpness property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting sharpness: {ex}")

    # try:
    #     result = True
    #     cam.SharpeningEnable.SetValue(PySpin.Camera.SharpeningEnableEnums.SharpeningEnable_Off)
    #     cam.SharpeningAuto.SetValue(False)
    #     cam.Sharpening.SetValue(sharpness)
    #     print(f"Sharpness set to: {sharpness}")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting sharpness: {ex}")
    #     result = False


def set_hue(cam: PySpin.CameraPtr, hue: int):
    """
    Sets the hue for the camera.

    :param cam: Camera to set hue for.
    :param hue: Hue value to set.
    :type cam: CameraPtr
    :type hue: int
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("Hue"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(hue)
    #         print(f"Hue set to: {hue}")
    #     else:
    #         print("Hue property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting hue: {ex}")

    try:
        # result = True
        cam.Hue.SetValue(hue)
        print(f"Hue set to: {hue}")
    except PySpin.SpinnakerException as ex:
        print(f"Error setting hue: {ex}")
        # result = False


def set_saturation(cam: PySpin.CameraPtr, saturation: int):
    """
    Sets the saturation for the camera.

    :param cam: Camera to set saturation for.
    :param saturation: Saturation value to set.
    :type cam: CameraPtr
    :type saturation: int
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("Saturation"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(saturation)
    #         print(f"Saturation set to: {saturation}")
    #     else:
    #         print("Saturation property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting saturation: {ex}")

    try:
        # result = True
        cam.SaturationEnable.SetValue(True)
        cam.Saturation.SetValue(saturation)
        print(f"Saturation set to: {saturation}")

    except PySpin.SpinnakerException as ex:
        print(f"Error setting saturation: {ex}")
        # result = False


def set_gamma(cam: PySpin.CameraPtr, gamma: int):
    """
    Sets the gamma for the camera.

    :param cam: Camera to set gamma for.
    :param gamma: Gamma value to set.
    :type cam: CameraPtr
    :type gamma: int
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("Gamma"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(gamma)
    #         print(f"Gamma set to: {gamma}")
    #     else:
    #         print("Gamma property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting gamma: {ex}")

    try:
        # result = True
        cam.Gamma.SetValue(gamma)
        print(f"Gamma set to: {gamma}")
    except PySpin.SpinnakerException as ex:
        print(f"Error setting gamma: {ex}")
        # result = False


def set_shutter(cam: PySpin.CameraPtr, shutter: float):
    """
    Sets the shutter for the camera.

    :param cam: Camera to set shutter for.
    :param shutter: Shutter value to set.
    :type cam: CameraPtr
    :type shutter: float
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("Shutter"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(shutter)
    #         print(f"Shutter set to: {shutter}")
    #     else:
    #         print("Shutter property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting shutter: {ex}")

    try:
        # result = True
        cam.Shutter.SetValue(shutter)
        print(f"Shutter set to: {shutter}")
    except PySpin.SpinnakerException as ex:
        print(f"Error setting shutter: {ex}")
        # result = False


def set_gain(cam: PySpin.CameraPtr, gain: float):
    """
    Sets the gain for the camera.

    :param cam: Camera to set gain for.
    :param gain: Gain value to set.
    :type cam: CameraPtr
    :type gain: float
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("Gain"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(gain)
    #         print(f"Gain set to: {gain}")
    #     else:
    #         print("Gain property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting gain: {ex}")

    try:
        # result = True
        cam.Gain.SetValue(gain)
        print(f"Gain set to: {gain}")
    except PySpin.SpinnakerException as ex:
        print(f"Error setting gain: {ex}")
        # result = False


def set_framerate(cam: PySpin.CameraPtr, framerate: float):
    """
    Sets the framerate for the camera.

    :param cam: Camera to set framerate for.
    :param framerate: Framerate value to set.
    :type cam: CameraPtr
    :type framerate: float
    """
    # try:
    #     prop = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("AcquisitionFrameRate"))
    #     if PySpin.IsWritable(prop):
    #         prop.SetValue(framerate)
    #         print(f"Framerate set to: {framerate}")
    #     else:
    #         print("Framerate property not writable.")
    # except PySpin.SpinnakerException as ex:
    #     print(f"Error setting framerate: {ex}")

    try:
        # result = True
        cam.AcquisitionFrameRateEnable.SetValue(True)
        cam.AcquisitionFrameRate.SetValue(framerate)
        print(f"Framerate set to: {framerate}")
    except PySpin.SpinnakerException as ex:
        print(f"Error setting framerate: {ex}")
        # result = False


def set_white_balance(cam: PySpin.CameraPtr, red: float, blue: float):
    """
    Sets the white balance for the camera.

    :param cam: Camera to set white balance for.
    :param red: Red channel value to set.
    :param blue: Blue channel value to set.
    :type cam: CameraPtr
    :type red: float
    :type blue: float
    """
    try:
        prop_red = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("BalanceRatioSelector"))
        prop_blue = PySpin.CFloatPtr(cam.GetNodeMap().GetNode("BalanceRatioSelector"))
        if PySpin.IsWritable(prop_red) and PySpin.IsWritable(prop_blue):
            prop_red.SetValue(red)
            prop_blue.SetValue(blue)
            print(f"White balance set to: Red={red}, Blue={blue}")
        else:
            print("White balance properties not writable.")
    except PySpin.SpinnakerException as ex:
        print(f"Error setting white balance: {ex}")


def set_panda_image_profile(cam: PySpin.CameraPtr):
    """
    Camera settings for the panda profile
    """
    print("Turning off auto settings...")
    # set_brightness(cam, 12.012)
    set_exposure(cam, 1.392)
    set_sharpness(cam, 1024)
    set_hue(cam, 0.0)
    set_saturation(cam, 100)
    set_gamma(cam, 1.250)
    set_shutter(cam, 50.023)
    set_gain(cam, 0.0)
    set_framerate(cam, 5)
    set_white_balance(cam, 762, 813)


# def epanda_camera_profile(self):
#     """Camera settings for the epanda profile"""
#     self.set_brightness(12.012)
#     self.set_exposure(1.392)
#     self.set_sharpness(1024)
#     self.set_hue(0.0)
#     self.set_saturation(100)
#     self.set_gamma(1.250)
#     self.set_shutter(50.023)
#     self.set_gain(0.0)
#     self.set_framerate(5)
#     self.set_white_balance(762, 813)
#     self.enable_embedded_image_info()

#     def set_brightness(self, brightness):
#         """Sets the brightness for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.BRIGHTNESS
#             brightness_property = self.camera.getProperty(prop)
#             brightness_property.absControl = True
#             brightness_property.absValue = brightness
#             self.camera.setProperty(brightness_property)
#             self.camera_logger.debug("Brightness set to: %d", brightness)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting brightness: %s", fc2_err)

#     def set_exposure(self, exposure_time):
#         """Sets the exposure time for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.AUTO_EXPOSURE
#             auto_exposure = self.camera.getProperty(prop)
#             auto_exposure.autoManualMode = False
#             auto_exposure.absControl = True
#             auto_exposure.onOff = True
#             auto_exposure.autoManualMode = False
#             auto_exposure.absValue = exposure_time
#             self.camera.setProperty(auto_exposure)
#             self.camera_logger.debug("Exposure time set to: %d", exposure_time)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting exposure time: %s", fc2_err)

#     def set_sharpness(self, sharpness):
#         """Sets the sharpness for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.SHARPNESS
#             sharpness_property = self.camera.getProperty(prop)
#             sharpness_property.absControl = True
#             sharpness_property.absValue = sharpness
#             self.camera.setProperty(sharpness_property)
#             self.camera_logger.debug("Sharpness set to: %d", sharpness)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting sharpness: %s", fc2_err)

#     def set_hue(self, hue):
#         """Sets the hue for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.HUE
#             hue_property = self.camera.getProperty(prop)
#             hue_property.absControl = True
#             hue_property.absValue = hue
#             self.camera.setProperty(hue_property)
#             self.camera_logger.debug("Hue set to: %d", hue)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting hue: %s", fc2_err)

#     def set_saturation(self, saturation):
#         """Sets the saturation for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.SATURATION
#             saturation_property = self.camera.getProperty(prop)
#             saturation_property.absControl = True
#             saturation_property.absValue = saturation
#             self.camera.setProperty(saturation_property)
#             self.camera_logger.debug("Saturation set to: %d", saturation)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting saturation: %s", fc2_err)

#     def set_gamma(self, gamma):
#         """Sets the gamma for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.GAMMA
#             gamma_property = self.camera.getProperty(prop)
#             gamma_property.absControl = True
#             gamma_property.onOff = True
#             gamma_property.absValue = gamma
#             self.camera.setProperty(gamma_property)
#             self.camera_logger.debug("Gamma set to: %d", gamma)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting gamma: %s", fc2_err)

#     def set_shutter(self, shutter):
#         """Sets the shutter for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.SHUTTER
#             shutter_property = self.camera.getProperty(prop)
#             shutter_property.absControl = True
#             shutter_property.onOff = True
#             shutter_property.autoManualMode = False
#             shutter_property.absValue = shutter
#             self.camera.setProperty(shutter_property)
#             self.camera_logger.debug("Shutter set to: %d", shutter)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting shutter: %s", fc2_err)

#     def set_gain(self, gain):
#         """Sets the gain for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.GAIN
#             gain_property = self.camera.getProperty(prop)
#             gain_property.absControl = True
#             gain_property.onOff = True
#             gain_property.autoManualMode = False
#             gain_property.absValue = gain
#             self.camera.setProperty(gain_property)
#             self.camera_logger.debug("Gain set to: %d", gain)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting gain: %s", fc2_err)

#     def set_framerate(self, framerate):
#         """Sets the framerate for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.FRAME_RATE
#             framerate_property = self.camera.getProperty(prop)
#             framerate_property.absControl = True
#             framerate_property.onOff = True
#             framerate_property.autoManualMode = False
#             framerate_property.absValue = framerate
#             self.camera.setProperty(framerate_property)
#             self.camera_logger.debug("Framerate set to: %d", framerate)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting framerate: %s", fc2_err)

#     def set_white_balance(self, red, blue):
#         """Sets the white balance for the camera"""
#         try:
#             prop = PyCapture2.PROPERTY_TYPE.WHITE_BALANCE
#             wb = self.camera.getProperty(prop)
#             wb.onOff = True
#             wb.absControl = False
#             wb.autoManualMode = False
#             wb.valueA = red
#             wb.valueB = blue
#             self.camera.setProperty(wb)
#             self.camera_logger.debug("White balance set to: %d %d", red, blue)
#         except PyCapture2.Fc2error as fc2_err:
#             self.camera_logger.debug("Error setting white balance: %s", fc2_err)

#     def epanda_camera_profile(self):
#         """Camera settings for the epanda profile"""
#         self.camera_logger.debug("Turning off auto settings...")
#         self.set_brightness(12.012)
#         self.set_exposure(1.392)
#         self.set_sharpness(1024)
#         self.set_hue(0.0)
#         self.set_saturation(100)
#         self.set_gamma(1.250)
#         self.set_shutter(50.023)
#         self.set_gain(0.0)
#         self.set_framerate(5)
#         self.set_white_balance(762, 813)
#         self.enable_embedded_image_info()

#     def enable_embedded_image_info(self):
#         """Enable embedding of various camera settings"""
#         embedded_info = self.camera.getEmbeddedImageInfo()
#         if embedded_info.available.timestamp:
#             self.camera.setEmbeddedImageInfo(timestamp=True)
#         else:
#             print("Timestamp is not available.")

#         if embedded_info.available.frameCounter:
#             self.camera.setEmbeddedImageInfo(frameCounter=True)
#         else:
#             print("Frame counter is not available.")

#         if embedded_info.available.gain:
#             self.camera.setEmbeddedImageInfo(gain=True)
#         else:
#             print("Gain is not available.")

#         if embedded_info.available.shutter:
#             self.camera.setEmbeddedImageInfo(shutter=True)
#         else:
#             print("Shutter is not available.")

#         if embedded_info.available.brightness:
#             self.camera.setEmbeddedImageInfo(brightness=True)
#         else:
#             print("Brightness is not available.")

#         if embedded_info.available.exposure:
#             self.camera.setEmbeddedImageInfo(exposure=True)
#         else:
#             print("Exposure is not available.")

#         if embedded_info.available.whiteBalance:
#             self.camera.setEmbeddedImageInfo(whiteBalance=True)
#         else:
#             print("White balance is not available.")

#         if embedded_info.available.ROIPosition:
#             self.camera.setEmbeddedImageInfo(ROIPosition=True)
#         else:
#             print("ROI position is not available.")


if __name__ == "__main__":
    # This function locates all connected cameras
    locate_connected_cameras()
    pyspin_system: PySpin.SystemPtr = PySpin.System.GetInstance()
    camera_list = pyspin_system.GetCameras()

    # Run example on each camera
    for instance, camera in enumerate(camera_list):
        print(f"Running example for camera {instance + 1}...")
        print(f"Applying panda profile to camera {instance + 1}...")
        # set_panda_image_profile(camera)
        RESULT = run_single_camera(camera, num_images=1)
        if RESULT:
            print(f"Camera {instance + 1} example complete...")
        else:
            print(f"Camera {instance + 1} example failed...")
    # Clear camera list before releasing system
    camera_list.Clear()

    # Release system instance
    pyspin_system.ReleaseInstance()

    input("Done! Press Enter to exit...")
