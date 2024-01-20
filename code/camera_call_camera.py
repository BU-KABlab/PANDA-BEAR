"""running pycapture-test.py from python 3.11"""

# Call pycapture-test.py from python 3.11 using python 3.6 envrionment using subprocess
# import subprocess
# from pathlib import Path
# file_path = Path(r"code\camera-pycapture-test.py")
# env_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\python360\\python.exe")
# subprocess.run([env_path, file_path], check= False, shell = True)

import subprocess
from pathlib import Path

def capture_new_image(save=True, num_images=1, file_name:Path="test.png") -> None:
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
            "--save_path",
            str(file_name.parent),
            "--file_name",
            str(file_name.name),
        ],
        check=False,
        shell=True,
    )

if __name__ == "__main__":
    from pathlib import Path
    from config.config import PATH_TO_DATA
    from experiment_class import EchemExperimentBase, ExperimentStatus

    instructions = EchemExperimentBase(
        id=1,
        well_id="A1",
        experiment_name="test",
        priority=1,
        pin=1,
        project_id=1,
        project_campaign_id=1,
        solutions={"5mm_fecn6": 0, "electrolyte": 120, "rinse0": 120},
        solutions_corrected={"5mm_fecn6": 0, "electrolyte": 120, "rinse0": 120},
        pumping_rate=0.3,
        status=ExperimentStatus.NEW,
        filename="test",
    )
    FILE_NAME =  "_".join([
                 str(instructions.project_id),
                 str(instructions.project_campaign_id),
                 str(instructions.id),
                 str(instructions.well_id),
                 "image"
            ])
    file_path=Path(PATH_TO_DATA / str(FILE_NAME)).with_suffix(".png")

    while file_path.exists():
        i = 1
        FILE_NAME = "_".join([
            str(instructions.project_id)
            ,str(instructions.project_campaign_id)
            ,str(instructions.id)
            ,str(instructions.well_id)
            ,"image"
            ,str(i)]
            )
        file_path=Path(PATH_TO_DATA / str(FILE_NAME)).with_suffix(".png")
        i += 1
    capture_new_image(
        save=True, num_images=1, file_name=file_path
    )
