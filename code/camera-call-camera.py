"""running pycapture-test.py from python 3.11"""

# Call pycapture-test.py from python 3.11 using python 3.6 envrionment using subprocess
# import subprocess
# from pathlib import Path
# file_path = Path(r"code\camera-pycapture-test.py")
# env_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\python360\\python.exe")
# subprocess.run([env_path, file_path], check= False, shell = True)

import subprocess
from pathlib import Path

def capture_new_image(save=True, num_images=1, file_name="test.png") -> None:
    """Capture a new image from the camera"""
    # Path to the Python interpreter
    python_360_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\python360\\python.exe")

    # Path to the script to run
    script_path = Path("code/camera.py")

    # Start a new process with the Python interpreter
    subprocess.run(
        [
            python_360_path,
            script_path,
            "--save",
            str(save),
            "--num_images",
            str(num_images),
            "--file_name",
            str(file_name),
        ],
        check=False,
        shell=True,
    )

if __name__ == "__main__":
    capture_new_image()
