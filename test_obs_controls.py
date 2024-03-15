import base64
from io import BytesIO

from obsws_python.error import OBSSDKRequestError
from PIL import Image

from epanda_lib.obs_controls import OBSController

obs = OBSController()

try:
    #obs.client.save_source_screenshot("Webcam", "png", "images", 1920, 1080, -1)
    screenshot = obs.client.get_source_screenshot("Webcam", "png", 1920, 1080, -1)
    img = Image.open(BytesIO(base64.b64decode(screenshot.image_data.split(',')[1])))
    img.show()
except OBSSDKRequestError as e:
    print(f"Failed to save screenshot: {e}")

