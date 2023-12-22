"""running pycapture-test.py from python 3.11"""

# Call pycapture-test.py from python 3.11 using python 3.6 envrionment using subprocess
import subprocess
from pathlib import Path
file_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\py_capture_test\\PyCapture2\\examples\\FlyCapture2Test.py")
env_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\py_capture_test\\python.exe")
subprocess.run([env_path, file_path], check= False, shell = True)
