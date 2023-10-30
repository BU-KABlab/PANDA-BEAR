# -*- coding: utf-8 -*-

"""
Python Interface for
Sartorius Serial Interface for
EA, EB, GD, GE, TE scales.

2010-2011 Robert Gieseke - robert.gieseke@gmail.com
See LICENSE.
"""

import serial
import logging
scale_logger = logging.getLogger(__name__)
scale_logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s,%(name)s,%(levelname)s,%(message)s")
system_handler = logging.FileHandler("code/logs/scale_testing.log")
system_handler.setFormatter(formatter)
scale_logger.addHandler(system_handler)

class Sartorius(serial.Serial):
    """
    Sartorius Serial Interface for
    EA, EB, GD, GE, TE scales.
    """
    def __init__(self, com_port: str = 'COM6'):
        """
        Initialise Sartorius device.

            Example:
            scale = Sartorius('COM1')
        """
        serial.Serial.__init__(self, com_port)
        self.baudrate = 9600
        self.bytesize = 7
        self.parity = serial.PARITY_ODD
        self.timeout = 0.5

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def value(self):
        """
        Return displayed scale value.
        """
        try:
            if self.inWaiting() == 0:
                self.write(b'\033P\n')
            answer = self.readline().decode()
            if len(answer) == 16: # menu code 7.1.1
                answer = float(answer[0:11].replace(' ', ''))
            else: # menu code 7.1.2
                answer = float(answer[6:17].replace(' ',''))
            return answer
        except Exception as e:
            return "NA"

    def display_unit(self):
        """
        Return unit.
        """
        self.write(b'\033P\n')
        answer = self.readline()
        try:
            answer = answer[11].strip()
        except:
            answer = "No answer"
        return answer

    def tara_zero(self):
        """
        Tara and zeroing combined.
        """
        self.write(b'\033T\n')

    def tara(self):
        """
        Tara.
        """
        self.write(b'\033U\n')

    def zero(self):
        """
        Zero.
        """
        self.write(b'\033V\n')

class MockSartorius:
    """
    Mock Sartorius Serial Interface for
    EA, EB, GD, GE, TE scales.
    """
    def __init__(self, com_port: str = 'COM6'):
        """
        Initialise Sartorius device.

            Example:
            scale = Sartorius('COM1')
        """
        self.com_port = com_port
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def value(self):
        """
        Return displayed scale value.
        """
        return 0.0

    def display_unit(self):
        """
        Return unit.
        """
        return "g"

    def tara_zero(self):
        """
        Tara and zeroing combined.
        """
        pass

    def tara(self):
        """
        Tara.
        """
        pass

    def zero(self):
        """
        Zero.
        """
        pass

    def close(self):
        """
        Close connection.
        """
        pass

def scale_variance_check():
    """
    Log multiple series of reading from the scale to determine the variance in the readings. 

    Check will consist of three regimes:
    10s between readings    
    5s between readings
    1s between readings

    """
    import time
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt
    import datetime
    import os
    import sys

    scale_logger.info("Starting scale variance check")
    scale_logger.info("Current working directory: %s", os.getcwd())
    scale_logger.info("Python version: %s", sys.version)
    scale_logger.info("Numpy version: %s", np.__version__)
    scale_logger.info("Matplotlib version: %s", matplotlib.__version__)
    scale_logger.info("Time: %s", datetime.datetime.now())

    scale_logger.info("Creating scale object")
    scale = Sartorius('COM6')
    scale_logger.info("Scale object created")

    scale_logger.info("Creating data arrays")
    scale_logger.info("Creating 10s array")
    ten_sec_array = np.zeros(100)
    scale_logger.info("Creating 5s array")
    five_sec_array = np.zeros(200)
    scale_logger.info("Creating 1s array")
    one_sec_array = np.zeros(1000)
    scale_logger.info("Data arrays created")

    scale_logger.info("Starting 10s loop")
    for i in range(100):
        ten_sec_array[i] = scale.value()
        time.sleep(10)
    scale_logger.info("10s loop complete")

    time.sleep(10)

    scale_logger.info("Starting 5s loop")
    for i in range(200):
        five_sec_array[i] = scale.value()
        time.sleep(5)
    scale_logger.info("5s loop complete")

    time.sleep(10)

    scale_logger.info("Starting 1s loop")
    for i in range(1000):
        one_sec_array[i] = scale.value()
        time.sleep(1)
    scale_logger.info("1s loop complete")

    scale_logger.info("Closing scale object")
    scale.close()
    scale_logger.info("Scale object closed")

    scale_logger.info("Plotting data")
    plt.figure()
    plt.subplot(3,1,1)
    plt.plot(ten_sec_array)
    plt.title("10s between readings")
    plt.ylabel("Reading (g)")
    plt.subplot(3,1,2)
    plt.plot(five_sec_array)
    plt.title("5s between readings")
    plt.ylabel("Reading (g)")
    plt.subplot(3,1,3)
    plt.plot(one_sec_array)
    plt.title("1s between readings")
    plt.ylabel("Reading (g)")
    plt.xlabel("Reading number")
    plt.savefig("code/logs/scale_testing.png")
    plt.show()
    scale_logger.info("Plotting complete")


if __name__ == '__main__':
    sartorius_scale = Sartorius('COM6')
    print(sartorius_scale.value())
    print(sartorius_scale.display_unit())
    sartorius_scale.tara_zero()
    print(sartorius_scale.value())
    sartorius_scale.tara()
    print(sartorius_scale.value())
    sartorius_scale.zero()
    print(sartorius_scale.value())
    sartorius_scale.close()