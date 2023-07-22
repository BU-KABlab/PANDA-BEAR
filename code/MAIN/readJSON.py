import json
import os
import sys
import time
import datetime
import pathlib

instructions = []
def readJSON(filename: str):
    
    cwd = pathlib.Path().absolute()
    file_path = pathlib.Path(cwd.parents[0].__str__() + "/instructions")
    file_to_open = file_path / filename
    with open(file_to_open, 'r') as f:
        data = json.load(f)
    return data

readJSON('experimentParameters_07_21_23_18_12.json')