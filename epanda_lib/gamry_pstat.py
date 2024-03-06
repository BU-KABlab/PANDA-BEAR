"""Module to inferface with Gamry Potentiostat"""
import datetime
import gc
import logging
import pathlib
import time

from comtypes import client
import numpy as np
import pandas as pd
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)


class GamryPotentiostat:
    """Class to interface with Gamry Potentiostat

    Attributes:
        pstat: Gamry Potentiostat
        devices: Gamry Device List
        gamry_com: Gamry COM
        dtaq: Gamry Data Acquisition
        signal: Gamry Signal
        dtaq_sink: Gamry Data Acquisition Events
        connection: Gamry Connection
        active: Gamry Active
        complete_file_name: Gamry Complete File Name

    """
    def __init__(self):
        self.pstat = None
        self.devices = None
        self.gamry_com = None
        self.dtaq = None
        self.signal = None
        self.dtaq_sink = None
        self.connection = None
        self.active = None
        self.complete_file_name = None

    def __enter__(self):
        self.connect_pstat()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect_pstat()

    def connect_pstat(self):
        """Connects to the Gamry Potentiostat and initializes the GamryDtaqEvents instance"""
        self.gamry_com = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
        self.pstat = client.CreateObject("GamryCOM.GamryPC6Pstat")
        self.devices = client.CreateObject("GamryCOM.GamryDeviceList")
        self.pstat.Init(self.devices.EnumSections()[0])  # grab the first pstat
        self.pstat.Open()  # open connection to pstat

        if self.devices.EnumSections():
            logger.debug("\tPstat connected: %s", self.devices.EnumSections()[0])
        else:
            logger.debug("\tPstat not connected")

        # Initialize the GamryDtaqEvents instance
        self.dtaq_sink = self.GamryDtaqEvents(self.dtaq, self.complete_file_name, self.pstat)

    class GamryDtaqEvents():
        """Class to handle events from the GamryDtaq object"""
        def __init__(self, dtaq_value, complete_file_name, potentiostat):
            self.dtaq = dtaq_value
            self.acquired_points = []
            self.complete_file_name = complete_file_name
            self.potentiostat = potentiostat

        # Other methods for handling events

        def cook(self):
            """Cook the data from the GamryDtaq object"""
            count = 1
            while count > 0:
                count, points = self.dtaq.Cook(10)
                self.acquired_points.extend(zip(*points))

        def on_data_available(self):
            """Call the cook method"""
            self.cook()

        def on_data_done(self):
            """Call the stop_acq method"""
            self.cook()
            time.sleep(2.0)
            self.call_stopacq()
            self.call_savedata(self.complete_file_name)

        def call_stopacq(self):
            """Call the stop_acq method"""
            self.potentiostat.stop_acq()

        def call_savedata(self, complete_file_name):
            """Call the save_data method"""
            self.potentiostat.save_data(complete_file_name, self.acquired_points)

    # methods for controlling the potentiostat

    def disconnect_pstat(self):
        """Disconnect the potentiostat"""
        if self.pstat:
            self.pstat.Close()
            time.sleep(15)

    def stop_acq(self):
        """Stop the acquisition"""
        self.active = False
        self.pstat.SetCell(self.gamry_com.CellOff)
        time.sleep(1)
        gc.collect()
        return

    def save_data(self, complete_file_name, acquired_points):
        """Save the data to a file"""
        output = pd.DataFrame(acquired_points)
        np.savetxt(complete_file_name.with_suffix(".txt"), output)
        logger.debug("Data saved")

    def set_filename(self, experiment_id, experiment_type):
        """Set the file name for the experiment"""
        current_time = datetime.datetime.now()
        file_date = current_time.strftime("%Y-%m-%d")
        cwd = pathlib.Path().absolute()
        file_path_par = pathlib.Path(f"{cwd.parents[1]}/data")
        file_path = file_path_par / file_date
        self.complete_file_name = file_path / f"experiment-{experiment_id}_{experiment_type}"
        logger.debug("eChem: complete file name is: %s", self.complete_file_name)
        if not pathlib.Path.exists(file_path):
            logger.debug("Folder does not exist. Making folder: %s", file_path)
            pathlib.Path.mkdir(file_path, parents=True, exist_ok=True)
        else:
            logger.debug("Folder %s exists", file_path)
        return self.complete_file_name

    def activecheck(self):
        """Check if the potentiostat is active"""
        while self.active is True:
            client.PumpEvents(1)
            time.sleep(0.5)


    def check_vsig_range(self, filename):
        """Check if the Vsig is in the valid range"""
        try:
            ocp_data = pd.read_csv(
                filename,
                sep=" ",
                header=None,
                names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"],
            )
            vsig_last_row_scientific = ocp_data.iloc[-2, ocp_data.columns.get_loc("Vsig")]
            logger.debug("Vsig last row: %s", vsig_last_row_scientific)
            vsig_last_row_decimal = float(vsig_last_row_scientific)
            logger.debug("Vsig last row: %f", vsig_last_row_decimal)

            if -1 < vsig_last_row_decimal and vsig_last_row_decimal < 1:
                logger.debug("Vsig in valid range (-1 to 1). Proceeding to echem experiment")
                return True
            else:
                logger.debug("Vsig not in valid range. Aborting echem experiment")
                return False
        
        except Exception as exception:
            logger.debug("Error occurred while checking Vsig: %s", exception)
            return False

    def cyclic(self, CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
        logger.debug("cyclic: made it to run")
        self.signal = client.CreateObject("GamryCOM.GamrySignalRupdn")
        self.dtaq = client.CreateObject("GamryCOM.GamryDtaqRcv")
        self.dtaq_sink = self.GamryDtaqEvents(self.dtaq, self.complete_file_name)
        self.connection = client.GetEvents(self.dtaq, self.dtaq_sink)

        self.signal.Init(
            self.pstat,
            CVvi,
            CVap1,
            CVap2,
            CVvf,
            CVsr1,
            CVsr2,
            CVsr3,
            0.0,
            0.0,
            0.0,
            CVsamplerate,
            CVcycle,
            self.gamry_com.PstatMode,
        )


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_cv_parameters:
    """CV Setup Parameters"""

    # CV Setup Parameters
    CVvi: float = 0.0  # initial voltage
    CVap1: float = 0.3
    CVap2: float = -0.2
    CVvf: float = -0.2
    CVstep: float = 0.01  # testing step, 100 mv/s
    CVsr1: float = 0.1
    CVcycle: int = 3
    CVsr2: float = CVsr1
    CVsr3: float = CVsr1
    CVsamplerate: float = CVstep / CVsr1


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_ca_parameters:
    """CA Setup Parameters"""

    # CA/CP Setup Parameters
    CAvi: float = 0.0  # Pre-step voltage (V)
    CAti: float = 0.0  # Pre-step delay time (s)
    CAv1: float = -2.4  # Step 1 voltage (V)
    CAt1: float = 300.0  # run time 300 seconds
    CAv2: float = 0.0  # Step 2 voltage (V)
    CAt2: float = 0.0  # Step 2 time (s)
    CAsamplerate: float = 0.05  # sample period (s)
    # Max current (mA)
    # Limit I (mA/cm^2)
    # PF Corr. (ohm)
    # Equil. time (s)
    # Expected Max V (V)
    # Initial Delay on
    # Initial Delay (s)


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_ocp_parameters:
    """OCP Setup Parameters"""

    # OCP Setup Parameters
    OCPvi: float = 0.0
    OCPti: float = 15.0
    OCPrate: float = 0.5


if __name__ == "__main__":
    with GamryPotentiostat() as gamry:
        try:
            # Use the gamry instance to perform experiments and control the Potentiostat

            # For example:
            # gamry.cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
            # gamry.chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
            # gamry.ocp(OCPvi, OCPti, OCPrate)
            pass  # Your code here

        except (ConnectionError, TimeoutError, ValueError) as e:
            # Handle specific exceptions here
            logger.error("An error occurred: %s", e)
