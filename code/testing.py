"""For building new protocols and testing new features."""
#
import logging
from pump_control import Pump
from mill_control import Mill, Instruments
from wellplate import Wells
import gamry_control_WIP as echem
from scale import Sartorius as Scale
from experiment_class import Experiment, ExperimentResult
from controller import read_vials, update_vial_state_file
from e_panda import mixing_test_protocol, peg2p_protocol
from mixing_test_experiments import experiments as mix_test_experiments
from peg2p_experiments import experiments as peg2p_experiments
from scheduler import Scheduler
from config.file_locations import *

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter(
    "%(asctime)s:%(name)s:%(levelname)s:%(custom1)s:%(custom2)s:%(message)s"
)
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

AIR_GAP = 40  # ul


class CustomLoggingFilter(logging.Filter):
    """This is a filter which injects custom values into the log record.
    From: https://stackoverflow.com/questions/56776576/how-to-add-custom-values-to-python-logging
    The values will be the experiment id and the well id
    """

    def __init__(self, custom1, custom2):
        super().__init__()
        self.custom1 = custom1
        self.custom2 = custom2

    def filter(self, record):
        record.custom1 = self.custom1
        record.custom2 = self.custom2
        return True


def cv_cleaning_test():
    """A protocol to test the cleaning of the platinum electrode using CV in pure electrolyte."""
    with Mill() as mill:
        echem.pstatconnect()
        wellplate = Wells(
            a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13
        )
        # define coordinates for easy reference
        a1_coord = wellplate.get_coordinates("A1")
        a2_coord = wellplate.get_coordinates("A2")
        a3_coord = wellplate.get_coordinates("A3")
        a4_coord = wellplate.get_coordinates("A4")

        ## Well 1: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        mill.safe_move(a1_coord["x"], a1_coord["y"], a1_coord["echem_height"])
        input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W1", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(echem.potentiostat_cv_parameters.CVstep / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        input("Press enter to start continue to well 2.")

        ## Well 2: Deposition using polymers (CA V=-1.7V, 300s)
        mill.safe_move(
            a2_coord["x"],
            a2_coord["y"],
            a2_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W2", "CA")
        echem.chrono(
            echem.potentiostat_ca_parameters.CAvi,
            echem.potentiostat_ca_parameters.CAti,
            CAv1=-1.7,
            CAt1=300,
            CAv2=echem.potentiostat_ca_parameters.CAv2,
            CAt2=echem.potentiostat_ca_parameters.CAt2,
            CAsamplerate=0.01,
        )  # CA

        echem.activecheck()
        mill.rinse_electrode()
        input("Press enter to continue to well 3.")

        ## Well 3: Cleaning in pure electrolyte (CV, 10 cycles, -1.5V to 1.5V)
        mill.safe_move(
            a3_coord["x"],
            a3_coord["y"],
            a3_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        input("Press enter to start CV cleaning")
        echem.setfilename("cleaning_test_W3", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=1.5,
            CVap2=-1.5,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(echem.potentiostat_cv_parameters.CVstep / 0.05),
            CVcycle=10,
        )
        echem.activecheck()
        mill.rinse_electrode()
        input("Press enter to start continue to well 4.")

        ## Well 4: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        mill.safe_move(
            a4_coord["x"],
            a4_coord["y"],
            a4_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        input("Press enter to continue.")
        echem.setfilename("cleaning_test_W4", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(echem.potentiostat_cv_parameters.CVstep / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        mill.rinse_electrode()
        input("Press enter to end")
        echem.disconnectpstat()


def peg2p_test(experiments: list[Experiment]):
    """
    Experiments for 3.4k PEG2P test

        Well | Solution(s)  | Deposition  | Characterization
        -----------------------------------------------------------------------
        G10  | DmFc         | None        | DmFc, 50 mV/s, 2 mV/step, 3 cycles
        G11  | PEG2Pc       | 1.2 V, 600s | DmFc, 50 mV/s, 2 mV/step, 3 cycles
        G12  | PEG2Pc       | 1.5 V, 600s | DmFc, 50 mV/s, 2 mV/step, 3 cycles
        H1   | PEG2Pc       | 1.2 V, 600s | DmFc, 50 mV/s, 2 mV/step, 3 cycles
        H2   | PEG2Pc       | 1.5 V, 600s | DmFc, 50 mV/s, 2 mV/step, 3 cycles
        H3   | DmFc         | None        | DmFc, 50 mV/s, 2 mV/step, 3 cycles


    The following steps will be performed for each well:
        - deposition using the deposition parameters listed
        - rinsing of the electrode
        - clearing of the well
        - rinsing of the well
        - characterizing (CV) the well
        - rinsing the electrode
        - clearing the well
        - rinsing the well

    """
    stock_vials = read_vials(STOCK_STATUS_FILE)
    waste_vials = read_vials(WASTE_STATUS_FILE)
    wellplate = Wells(a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13)
    scheduler = Scheduler()
    with Mill() as mill:
        mill.homing_sequence()
        with Scale() as scale:
            pump = Pump(mill, scale)
            echem.pstatconnect()
            for experiment in experiments:
                ## save the experiment to the experiment queue
                scheduler.add_experiment(experiment)
                results = ExperimentResult()
                (
                    experiment,
                    results,
                    stock_vials,
                    waste_vials,
                    wellplate,
                ) = peg2p_protocol(
                    experiment,
                    results,
                    mill,
                    pump,
                    stock_vials,
                    waste_vials,
                    wellplate,
                )

                ## Update the system state
                update_vial_state_file(stock_vials, STOCK_STATUS_FILE)
                update_vial_state_file(waste_vials, WASTE_STATUS_FILE)
                scheduler.change_well_status(
                    experiment.target_well,
                    experiment.status,
                    experiment.status_date,
                    experiment.id,
                )

                ## Update location of experiment instructions and save results
                scheduler.update_experiment_status(experiment)
                scheduler.update_experiment_location(experiment)
                scheduler.save_results(experiment, results)

                # Plot results
                # analyzer.plotdata(experiment.filename, Path.cwd() / "data" / experiment.filename)

            if echem.OPEN_CONNECTION is True:
                echem.disconnectpstat()


def mixing_test(experiments: list[Experiment]):
    """
    A protocol to test the mixing of the solution in the wellplate.
    Experiment name format: MixingTest_wellID_echemType

    The contents and variable parameters of each well are as follows:

    Well | Solution(s)              | Mixing repetitions
    --------------------------------------------------------
    C1   | Premixed Solution        | 0
    C2   | Premix                   | 0
    C3   | PEG, Acrylate, DmFc      | 1
    C4   | PEG, Acrylate, DmFc      | 1
    C5   | PEG, Acrylate, DmFc      | 3
    C6   | PEG, Acrylate, DmFc      | 3
    C7   | PEG, Acrylate, DmFc      | 6
    C8   | PEG, Acrylate, DmFc      | 6
    C9   | PEG, Acrylate, DmFc      | 9
    C10  | PEG, Acrylate, DmFc      | 9
    C11  | Premixed Solution        | 0
    C12  | Premixed Solution        | 0

    For each well, the following steps are also performed:
    - characterizing (CV) the well
    - plotting the results
    """
    stock_vials = read_vials("code\system state\stock_status.json")
    waste_vials = read_vials("code\system state\waste_status.json")
    wellplate = Wells(a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13)
    scheduler = Scheduler()
    with Mill() as mill:
        mill.homing_sequence()
        with Scale() as scale:
            pump = Pump(mill, scale)
            echem.pstatconnect()
            for experiment in experiments:
                ## save the experiment to the experiment queue
                scheduler.add_experiment(experiment)
                results = ExperimentResult()
                (
                    experiment,
                    results,
                    stock_vials,
                    waste_vials,
                    wellplate,
                ) = mixing_test_protocol(
                    experiment,
                    results,
                    mill,
                    pump,
                    stock_vials,
                    waste_vials,
                    wellplate,
                )

                ## Update the system state
                update_vial_state_file(
                    stock_vials, "code\system state\stock_status.json"
                )
                update_vial_state_file(
                    waste_vials, "code\system state\waste_status.json"
                )
                scheduler.change_well_status(
                    experiment.target_well,
                    experiment.status,
                    experiment.status_date,
                    experiment.id,
                )

                ## Update location of experiment instructions and save results
                scheduler.update_experiment_status(experiment)
                scheduler.update_experiment_location(experiment)
                scheduler.save_results(experiment, results)

                # Plot results
                # analyzer.plotdata(experiment.filename, Path.cwd() / "data" / experiment.filename)

            if echem.OPEN_CONNECTION is True:
                echem.disconnectpstat()


if __name__ == "__main__":
    # mixing_test(mix_test_experiments)
    peg2p_test(peg2p_experiments)
