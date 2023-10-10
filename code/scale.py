# -*- coding: utf-8 -*-

"""
Python Interface for
Sartorius Serial Interface for
EA, EB, GD, GE, TE scales.

2010-2011 Robert Gieseke - robert.gieseke@gmail.com
See LICENSE.
"""

import serial

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
        except:
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

if __name__ == '__main__':
    scale = Sartorius('COM6')
    print(scale.value())
    print(scale.display_unit())
    scale.tara_zero()
    print(scale.value())
    scale.tara()
    print(scale.value())
    scale.zero()
    print(scale.value())
    scale.close()