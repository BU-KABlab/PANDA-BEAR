"""a virtual pstat for testing main code logic"""
import logging
import pathlib
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

class GamryPotentiostat:
    def __init__(self):
        self.OPEN_CONNECTION = False

    def connect(self):
        self.OPEN_CONNECTION = True

    def disconnect(self):
        self.OPEN_CONNECTION = False

    def pstatdisconnect(self):
        self.OPEN_CONNECTION = False

    def OCP(self, OCPvi, OCPti, OCPrate):
        pass

    def activecheck(self):
        pass

    def check_vf_range(self, file):
        return True

    def setfilename(self, experiment_id, experiment_type):
        COMPLETE_FILE_NAME = (
            pathlib.Path.cwd()
            / "data"
            / ("experiment-" + str(experiment_id) + "_mock_" + experiment_type)
        )
        logger.debug("eChem: complete file name is: %s", COMPLETE_FILE_NAME)
        return COMPLETE_FILE_NAME

    def chrono(self, CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate):
        pass

    def cyclic(self, CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
        pass

    @dataclass(config=ConfigDict(validate_assignment=True))
    class potentiostat_cv_parameters:
        """CV Setup Parameters"""

        # CV Setup Parameters
        CVvi: float = 0.0  # initial voltage
        CVap1: float = 0.5 
        CVap2: float = -0.2 
        CVvf: float = 0.0  # final voltage
        CVstep: float = 0.01
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
        CAv1: float = -1.7  # Step 1 voltage (V)
        CAt1: float = 300.0  # run time 300 seconds
        CAv2: float = 0.0  # Step 2 voltage (V)
        CAt2: float = 0.0  # Step 2 time (s)
        CAsamplerate: float = 0.5  # sample period (s)
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
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
