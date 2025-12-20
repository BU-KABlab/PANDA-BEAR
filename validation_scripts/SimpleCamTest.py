import PySpin
import cv2

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()
cam = cam_list[0]

try:
    cam.Init()
    nodemap = cam.GetNodeMap()

    # Try to set RGB8 directly (camera does Bayer conversion)
    pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode("PixelFormat"))
    if PySpin.IsAvailable(pixel_format) and PySpin.IsWritable(pixel_format):
        rgb8_entry = pixel_format.GetEntryByName("RGB8")
        if rgb8_entry and PySpin.IsAvailable(rgb8_entry):
            pixel_format.SetIntValue(rgb8_entry.GetValue())
            print("Set format to RGB8 - camera will handle Bayer conversion")

    cam.BeginAcquisition()
    image_result = cam.GetNextImage(1000)

    if not image_result.IsIncomplete():
        print(f"Format: {image_result.GetPixelFormatName()}")
        image_data = image_result.GetNDArray()

        # If it's RGB, convert to BGR for OpenCV
        if image_result.GetPixelFormatName() == "RGB8":
            image_bgr = cv2.cvtColor(image_data, cv2.COLOR_RGB2BGR)
        else:
            image_bgr = image_data

        cv2.imwrite("camera_converted_color.jpg", image_bgr)
        print("Image saved with camera's internal color conversion")

    image_result.Release()

finally:
    try:
        cam.EndAcquisition()
    except:
        pass
    try:
        cam.DeInit()
    except:
        pass
    del cam
    cam_list.Clear()
    system.ReleaseInstance()
    print("Camera disconnected and system released")
    print("Done.")
