"""
The PANDA host is the main script that runs on the host machine. It is responsible for
- Recieving instructions from the PANDA client such as:
    - Start and stop the control loop
    - Pause and resume the control loop
    - Perform a calibration of the mill and item locations
    - Perform a calibration of the camera

- Sending prompts or information back to the client such as:
    - The current state of the control loop
    - calibration prompts
    - error messages

The PANDA host requires access to the PANDA db. On start up a connection to the db is established.
The PANDA host is responsible for updating the db with the current state of the control loop.
If a connection to the db is not established or lost the PANDA host will stop the control loop and
prompt the client for db connection information.

PANDA host is intended to run on a Debian based system. It is recommended to run the PANDA host on a
dedicated machine such as a Raspberry Pi 4+ or a Jetson Nano. The PANDA host requires a connection to
the PANDA db.
"""
