import PySpin
import time

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()

if cam_list.GetSize() == 0:
    print("No cameras detected.")
    system.ReleaseInstance()
    exit()

cam = cam_list[0]
cam.Init()
nodemap = cam.GetNodeMap()

# Lower resolution
width = PySpin.CIntegerPtr(nodemap.GetNode("Width"))
height = PySpin.CIntegerPtr(nodemap.GetNode("Height"))

if PySpin.IsAvailable(width) and PySpin.IsWritable(width):
    width.SetValue(min(640, width.GetMax()))
if PySpin.IsAvailable(height) and PySpin.IsWritable(height):
    height.SetValue(min(480, height.GetMax()))

# Disable chunk data (some models default to it and fail silently)
chunk_mode_active = PySpin.CBooleanPtr(nodemap.GetNode("ChunkModeActive"))
if PySpin.IsAvailable(chunk_mode_active) and PySpin.IsWritable(chunk_mode_active):
    chunk_mode_active.SetValue(False)
nodemap = cam.GetNodeMap()

# Disable trigger mode
trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerMode"))
trigger_source = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerSource"))

if PySpin.IsAvailable(trigger_mode) and PySpin.IsWritable(trigger_mode):
    # First disable trigger mode to configure it
    trigger_mode_off = trigger_mode.GetEntryByName("Off")
    trigger_mode.SetIntValue(trigger_mode_off.GetValue())

# Confirm it's off
print("Trigger mode disabled.")

# Start image acquisition
cam.BeginAcquisition()
time.sleep(0.5)
image_result = cam.GetNextImage(2000)

if image_result.IsIncomplete():
    print("Image incomplete with status", image_result.GetImageStatus())
else:
    filename = "image.jpg"
    image_result.Save(filename)
    print(f"Image saved as {filename}")

# Release image and stop acquisition
image_result.Release()
cam.EndAcquisition()
cam.DeInit()

# Clean up
del cam
cam_list.Clear()
del cam_list
system.ReleaseInstance()
