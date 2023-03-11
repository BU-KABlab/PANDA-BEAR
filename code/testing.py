import time,serial
from serial import tools

#Alphabetically lists the ports by name
def comslist():
    ports = []
    for i in serial.tools.list_ports.comports():
        try:
            ser = serial.Serial(i.name)
            ser.close()
        except serial.SerialException as e:
            print(e)
        else:
            ports.append(i.name)
    ports.sort()
    return ports

#Finds the desired port using the name eg COM1
def selectcom(port):
    try :
        ser = serial.Serial(port)
    except serial.SerialException as e:
        print(e)
    else:
        return ser

comslist()