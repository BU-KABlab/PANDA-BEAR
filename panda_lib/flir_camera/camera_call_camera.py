"""running pycapture-test.py from python 3.11"""

# Call pycapture-test.py from python 3.11 using python 3.6 envrionment using subprocess
# import subprocess
# from pathlib import Path
# file_path = Path(r"code\camera-pycapture-test.py")
# env_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\python360\\python.exe")
# subprocess.run([env_path, file_path], check= False, shell = True)

# import subprocess
from configparser import ConfigParser
from pathlib import Path
from PySpin import PySpin
from .camera import run_single_camera

# Read the config file
config = ConfigParser()
# config.read("panda_lib/config/panda_sdl_config.ini")
# PYTHON_360_PATH = config.get("GENERAL", "python_360_path")
# CAMERA_SCRIPT_PATH = "panda_lib/flir_camera/camera.py"
# if config.getboolean("OPTIONS", "testing"):
#     PATH_TO_DATA = Path(config.get("TESTING", "data_dir"))
# else:
#     PATH_TO_DATA = Path(config.get("PRODUCTION", "data_dir"))


# def capture_new_image(save=True, num_images=1, file_name:Path=Path("images/test.tiff")) -> Path:
#     """Capture a new image from the camera"""
#     # Path to the Python interpreter
#     python_360_path = PYTHON_360_PATH

#     # Path to the script to run
#     script_path = CAMERA_SCRIPT_PATH

#     if file_name.suffix != ".tiff":
#         file_name = file_name.with_suffix(".tiff")
#     # Start a new process with the Python interpreter
#     subprocess.run(
#         [
#             python_360_path,
#             script_path,
#             "--save",
#             str(save),
#             "--num_images",
#             str(num_images),
#             "--save_path",
#             str(file_name.parent),
#             "--file_name",
#             str(file_name.name),
#         ],
#         check=False,
#         shell=True,
#     )

#     return file_name

# if __name__ == "__main__":
#     FILE_NAME =  "test image"
#     file_path=Path(PATH_TO_DATA / str(FILE_NAME)).with_suffix(".png")
#     i=1
#     while file_path.exists():
#         file_path = file_path.with_name(file_path.stem + "_" + str(i) + file_path.suffix)
#         i+=1
#     capture_new_image(
#         save=True, num_images=1, file_name=file_path
#     )

def file_enumeration(file_path:Path) -> Path:
    i=1
    while file_path.exists():
        file_path = file_path.with_name(file_path.stem + "_" + str(i) + file_path.suffix)
        i+=1
    return file_path

def capture_new_image(save=True, num_images=1, file_name:Path=Path("images/test.tiff")) -> Path:
    """Capture a new image from the FLIR camera"""
    # Check the file name and ennumerate if it already exists
    file_name = file_enumeration(file_name)
    pyspin_system: PySpin.SystemPtr = PySpin.System.GetInstance()
    camera_list:PySpin.CameraList = pyspin_system.GetCameras()
    # Run example on each camera
    for _, camera in enumerate(camera_list):
        camera: PySpin.CameraPtr
        result = run_single_camera(camera, image_path=file_name.stem, num_images=num_images)
        if result:
            print(f"Camera {camera.DeviceID} took image...")
        else:
            print(f"Camera {camera.DeviceID} failed to take image...")
    # Clear camera list before releasing system
    camera_list.Clear()

    # Release system instance
    pyspin_system.ReleaseInstance()

    return file_name
