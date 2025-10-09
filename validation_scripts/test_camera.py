import PySpin
import cv2
import numpy as np

def capture_color_image():
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    
    if cam_list.GetSize() == 0:
        print("No cameras detected.")
        system.ReleaseInstance()
        return
    
    cam = cam_list[0]
    
    try:
        cam.Init()
        nodemap = cam.GetNodeMap()
        
        # Set resolution
        width = PySpin.CIntegerPtr(nodemap.GetNode("Width"))
        height = PySpin.CIntegerPtr(nodemap.GetNode("Height"))
        
        if PySpin.IsAvailable(width) and PySpin.IsWritable(width):
            width.SetValue(min(1280, width.GetMax()))
        if PySpin.IsAvailable(height) and PySpin.IsWritable(height):
            height.SetValue(min(960, height.GetMax()))
        
        # Disable auto exposure
        exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureAuto"))
        if PySpin.IsAvailable(exposure_auto) and PySpin.IsWritable(exposure_auto):
            exposure_auto_off = exposure_auto.GetEntryByName("Off")
            if exposure_auto_off:
                exposure_auto.SetIntValue(exposure_auto_off.GetValue())
        
        # Set manual exposure time
        exposure_time = PySpin.CFloatPtr(nodemap.GetNode("ExposureTime"))
        if PySpin.IsAvailable(exposure_time) and PySpin.IsWritable(exposure_time):
            exposure_time.SetValue(min(50000, exposure_time.GetMax()))
        
        # Try to set color format
        pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode("PixelFormat"))
        current_format = None
        
        if PySpin.IsAvailable(pixel_format) and PySpin.IsWritable(pixel_format):
            color_formats = ["BayerRG8", "BayerGR8", "BayerGB8", "BayerBG8", "RGB8", "BGR8"]
            
            for fmt in color_formats:
                try:
                    pixel_format_entry = pixel_format.GetEntryByName(fmt)
                    if pixel_format_entry and PySpin.IsAvailable(pixel_format_entry):
                        pixel_format.SetIntValue(pixel_format_entry.GetValue())
                        current_format = fmt
                        print(f"Pixel format set to: {fmt}")
                        break
                except PySpin.SpinnakerException:
                    continue
        
        # Disable trigger mode
        trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerMode"))
        if PySpin.IsAvailable(trigger_mode) and PySpin.IsWritable(trigger_mode):
            trigger_mode_off = trigger_mode.GetEntryByName("Off")
            if trigger_mode_off:
                trigger_mode.SetIntValue(trigger_mode_off.GetValue())
        
        # Start acquisition
        cam.BeginAcquisition()
        
        try:
            # Capture image
            image_result = cam.GetNextImage(1000)
            
            if image_result.IsIncomplete():
                print(f"Image incomplete with status {image_result.GetImageStatus()}")
            else:
                print(f"Captured image: {image_result.GetWidth()}x{image_result.GetHeight()}")
                print(f"Pixel format: {image_result.GetPixelFormatName()}")
                
                # Handle different pixel formats
                if current_format and current_format.startswith("Bayer"):
                    print("Processing Bayer pattern image...")
                    
                    # Check if Convert method exists (full PySpin)
                    if hasattr(image_result, 'Convert'):
                        print("Using PySpin Convert method...")
                        converted_image = image_result.Convert(PySpin.PixelFormat_RGB8, PySpin.HQ_LINEAR)
                        image_data = converted_image.GetNDArray()
                        image_bgr = cv2.cvtColor(image_data, cv2.COLOR_RGB2BGR)
                        cv2.imwrite("color_image.jpg", image_bgr)
                        converted_image.Release()
                    else:
                        print("Using manual Bayer conversion...")
                        # Get raw Bayer data
                        image_data = image_result.GetNDArray()
                        
                        # Convert Bayer to BGR using OpenCV
                        if current_format == "BayerRG8":
                            image_bgr = cv2.cvtColor(image_data, cv2.COLOR_BAYER_RG2BGR)
                        elif current_format == "BayerGR8":
                            image_bgr = cv2.cvtColor(image_data, cv2.COLOR_BAYER_GR2BGR)
                        elif current_format == "BayerGB8":
                            image_bgr = cv2.cvtColor(image_data, cv2.COLOR_BAYER_GB2BGR)
                        elif current_format == "BayerBG8":
                            image_bgr = cv2.cvtColor(image_data, cv2.COLOR_BAYER_BG2BGR)
                        else:
                            image_bgr = image_data  # Fallback
                        
                        cv2.imwrite("color_image.jpg", image_bgr)
                    
                    print("Color image saved as 'color_image.jpg'")
                    
                elif current_format in ["RGB8", "BGR8"]:
                    print("Saving direct RGB/BGR image...")
                    image_data = image_result.GetNDArray()
                    if current_format == "RGB8":
                        image_bgr = cv2.cvtColor(image_data, cv2.COLOR_RGB2BGR)
                    else:
                        image_bgr = image_data
                    cv2.imwrite("direct_color_image.jpg", image_bgr)
                    print("Direct color image saved as 'direct_color_image.jpg'")
                    
                else:
                    print("Saving raw image...")
                    image_data = image_result.GetNDArray()
                    cv2.imwrite("raw_image.jpg", image_data)
                    print("Raw image saved as 'raw_image.jpg'")
            
            # Always release the image
            image_result.Release()
            
        except PySpin.SpinnakerException as ex:
            print(f"Error during capture: {ex}")
        
        finally:
            try:
                cam.EndAcquisition()
            except:
                pass
    
    except PySpin.SpinnakerException as ex:
        print(f"Error during initialization: {ex}")
    
    finally:
        # Proper cleanup sequence
        try:
            cam.DeInit()
        except:
            pass
        
        try:
            del cam
        except:
            pass
        
        try:
            cam_list.Clear()
        except:
            pass
        
        try:
            system.ReleaseInstance()
        except:
            pass

if __name__ == "__main__":
    capture_color_image()
