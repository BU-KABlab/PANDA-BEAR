"""For building new protocols and testing new features."""
#
from pump_control import Pump
from mill_control import Mill, Instruments
from wellplate import Wells
from vials import Vial
import gamry_control_WIP as echem
from scale import Sartorius as Scale
#from controller import read_vials, update_vials
from experiment_class import Experiment, ExperimentResult, ExperimentStatus
from datetime import datetime
import logging
from typing import Tuple
from e_panda import read_vials, update_vials
import e_panda
import sys
import pytz as tz
from mixing_test_experiments import experiments as mix_test_experiments
from scheduler import Scheduler
import Analyzer as analyzer
from pathlib import Path

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


def interactive():
    # ferrocene_vial = stock_vials[4]
    # ferrocene_coordinates = ferrocene_vial.coordinates
    # mill.move_pipette_to_position(ferrocene_coordinates['x'],ferrocene_coordinates['y'],0)
    # mill.move_pipette_to_position(ferrocene_coordinates['x'],ferrocene_coordinates['y'],ferrocene_vial.bottom)

    # mill.move_electrode_to_position(wellplate.get_coordinates('F6')['x'], wellplate.get_coordinates('F6')['y'],0)
    # mill.move_electrode_to_position(wellplate.get_coordinates('F6')['x'], wellplate.get_coordinates('F6')['y'],-67)
    # mill.move_electrode_to_position(wellplate.get_coordinates('F6')['x'], wellplate.get_coordinates('F6')['y'], wellplate.depth('F6'))

    # mill.move_electrode_to_position(-200,-240,0)
    # mill.move_electrode_to_position(-200,-240,-20)
    # mill.rinse_electrode()
    with Mill() as mill:
        while True:
            print("Select an operation:")
            print("1. Move center to position")
            print("2. Move pipette to position")
            print("3. Move electrode to position")
            print("4. Exit")

            choice = input("Enter your choice (1/2/3/4): ")

            if choice == "1":
                x = float(input("Enter X coordinate: "))
                y = float(input("Enter Y coordinate: "))
                z = float(input("Enter Z coordinate: "))
                mill.move_center_to_position(x, y, z)
            elif choice == "2":
                x = float(input("Enter X coordinate: "))
                y = float(input("Enter Y coordinate: "))
                z = float(input("Enter Z coordinate: "))
                mill.move_pipette_to_position(x, y, z)
            elif choice == "3":
                x = float(input("Enter X coordinate: "))
                y = float(input("Enter Y coordinate: "))
                z = float(input("Enter Z coordinate: "))
                mill.move_electrode_to_position(x, y, z)

            elif choice == "4":
                print("Exiting program.")
                break
            else:
                print("Invalid choice. Please enter a valid option.")

        return 0

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
    wellplate = Wells(
        a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13
    )
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
                experiment, results, stock_vials, waste_vials, wellplate = mixing_test_protocol(
                    experiment,
                    results,
                    mill,
                    pump,
                    scale,
                    stock_vials,
                    waste_vials,
                    wellplate,
                )

                ## Update the system state
                update_vials(stock_vials, "code\system state\stock_status.json")
                update_vials(waste_vials, "code\system state\waste_status.json")
                scheduler.change_well_status(experiment.id, experiment.status)

                ## Update location of experiment instructions and save results
                scheduler.update_experiment_status(experiment)
                scheduler.update_experiment_location(experiment)
                scheduler.save_results(experiment, results)

                # Plot results
                #analyzer.plotdata(experiment.filename, Path.cwd() / "data" / experiment.filename)

            if echem.OPEN_CONNECTION is True:
                echem.disconnectpstat()


def mixing_test_protocol(
    instructions: Experiment,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    scale: Scale,
    stock_vials: list[Vial],
    waste_vials: list[Vial],
    wellplate: Wells,
) -> Tuple[Experiment, ExperimentResult, list[Vial], list[Vial], Wells]:
    """
    Run the standard experiment:
    1. Deposit solutions into well
        for each solution:
            a. Withdraw air gap
            b. Withdraw solution
            c. Purge
            d. Deposit into well
            e. Purge
            f. Blow out
            g. Flush pipette tip
    2. Mix solutions in well
    3. Flush pipette tip
    7. Characterize the film on the substrate
    8. Return results, stock_vials, waste_vials, wellplate

    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        mill (object): The mill object
        pump (object): The pump object
        scale (object): The scale object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
        wellplate (Wells object): The wellplate object

    Returns:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
        wellplate (Wells object): The wellplate object
    """
    # Add custom value to log format
    custom_filter = CustomLoggingFilter(instructions.id, instructions.target_well)
    logger.addFilter(custom_filter)

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        experiment_solutions = ["peg", "acrylate", "dmf", "custom","ferrocene"]
        e_panda.apply_log_filter(instructions.id, instructions.target_well)
        # Deposit all experiment solutions into well
        for solution_name in experiment_solutions:
            if (
                getattr(instructions, solution_name) > 0
                and solution_name[0:4] != "rinse"
            ):  # if there is a solution to deposit
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    getattr(instructions, solution_name),
                    solution_name,
                    instructions.target_well,
                )
                experiment_solutions, waste_vials, wellplate = e_panda.pipette(
                    volume=getattr(instructions, solution_name),
                    solutions=stock_vials,  # list of vial objects passed to ePANDA
                    solution_name=solution_name,  # from the list above
                    target_well=instructions.target_well,
                    pumping_rate=instructions.pumping_rate,
                    waste_vials=waste_vials,  # list of vial objects passed to ePANDA
                    waste_solution_name="waste",
                    wellplate=wellplate,
                    pump=pump,
                    mill=mill,
                    scale=scale,
                )

                stock_vials, waste_vials = e_panda.flush_pipette_tip(
                    pump,
                    waste_vials,
                    stock_vials,
                    instructions.flush_sol_name,
                    mill,
                    instructions.pumping_rate,
                    instructions.flush_vol,
                )
        logger.info("Pipetted solutions into well: %s", instructions.target_well)

        # Mix solutions in well
        if instructions.mix == 1:
            logger.info("Mixing well: %s", instructions.target_well)
            instructions.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(instructions.target_well),
                mix_repetitions=instructions.mix_count,
                mix_volume=instructions.mix_vol,
                mix_rate=instructions.mix_rate,
            )
            logger.info("Mixed well: %s", instructions.target_well)

            stock_vials, waste_vials = e_panda.flush_pipette_tip(
                pump,
                waste_vials,
                stock_vials,
                instructions.flush_sol_name,
                mill,
                instructions.pumping_rate,
                instructions.flush_vol,
            )

        # Echem CV - characterization
        if instructions.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instructions.target_well
            )
            # Deposit characterization solution into well

            instructions, results = e_panda.characterization(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.target_well)
            # Flushing procedure

        instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED\n\n", instructions.id)

    except e_panda.OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Failed instructions updated for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

    except Exception as general_exception:
        exception_type, _, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        logger.error("Exception: %s", general_exception)
        logger.error("Exception type: %s", exception_type)
        logger.error("File name: %s", filename)
        logger.error("Line number: %d", line_number)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        return instructions, results, stock_vials, waste_vials, wellplate

    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id
        )

    return instructions, results, stock_vials, waste_vials, wellplate

if __name__ == "__main__":
    #cv_cleaning_test()
    # main()
    # interactive()
    # dry_run_experiment = Experiment(
    #     id=0,
    #     priority=1,
    #     pin=CURRENT_PIN,
    #     target_well="C12",
    #     dmf=50,
    #     peg=50,
    #     acrylate=50,
    #     ferrocene=50,
    #     custom=90,
    #     ocp=1,
    #     ca=0,  # 0 = no deposition, 1 = deposition
    #     cv=1,  # 0 = no characterization, 1 = characterization
    #     baseline=0,
    #     dep_duration=0,
    #     dep_pot= 0,
    #     char_sol_name="ferrocene",
    #     char_vol= 0,
    #     flush_sol_name="dmf",
    #     flush_vol=120,
    #     rinse_count=0,
    #     rinse_vol=150,
    #     mix=1,  # 0 = no mixing, 1 = mixing
    #     mix_count=3,
    #     mix_vol=145,
    #     mix_rate=0.62,
    #     status=ExperimentStatus.NEW,
    #     status_date=datetime.now(),
    #     filename="mixing_test_dry_run_C12",
    #     results=None,
    # # )
    # dry_run_experiment.status = ExperimentStatus.RUNNING
    # scheduler = Scheduler()
    # scheduler.update_experiment_status(dry_run_experiment)
    
    # input("Press enter when stock vials are in place and status updated (code/system state/stock_status.json):")
    # input("Press enter to start dry run after switching pstat to test cell:")
    #mixing_test([dry_run_experiment])
    #input("Please change pstat back to working set up and press enter to continue:")
    #input("Press enter to continue to mixing test following successful dry run:")
    mixing_test(mix_test_experiments)
