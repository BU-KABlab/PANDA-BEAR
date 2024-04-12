""""""

import pandas as pd
from scipy.integrate import trapezoid
import re
import math

from . import RawMetrics, MLInput, PEDOTMetrics


def modify_function(value):
    # circular wells
    return (
        value * 100000 / (math.pi * 3.25 * 3.25)
    )  # converts the current from amps to milliamps and changes the current column to current density


# Calculate charge passed using text file for deposition
def calc_charge(deposition_file):
    # Read in the text file
    df = pd.read_csv(
        deposition_file,
        sep=" ",
        header=None,
        names=[
            "Time",
            "Vf",
            "Vu",
            "Im",
            "Q",
            "Vsig",
            "Ach",
            "IERange",
            "Over",
            "StopTest",
        ],
    )
    # Calculate the charge passed by integrating the current over time using the trapezoidal rule
    df_copy = df.copy()
    df_copy["Im"] = df_copy["Im"].apply(modify_function)

    charge = trapezoid(df_copy["Im"], df_copy["Time"])
    return charge


# Calculate metric for capacitance using CV by finding the area enclosed by the CV curve
def calc_capacitance(CV_file):
    df = pd.read_csv(
        CV_file,
        sep=" ",
        header=None,
        names=[
            "Time",
            "Vf",
            "Vu",
            "Im",
            "Vsig",
            "Ach",
            "IERange",
            "Overload",
            "StopTest",
            "Cycle",
            "Ach2",
        ],
    )
    df = df.dropna(subset=["Cycle"])
    df["Cycle"] = df["Cycle"].astype(int)
    df_second_cycle = df[df["Cycle"] == 1].copy()

    if len(df_second_cycle) == 0:
        print("No second cycle found")
        return None

    df_second_cycle["Im_mod"] = df_second_cycle["Im"].apply(modify_function)

    min_current = df_second_cycle["Im_mod"].min()
    df_second_cycle["Im_shifted"] = df_second_cycle["Im_mod"] - min_current + 0.0001
    max_voltage_index = df_second_cycle["Vf"].idxmax()

    ascending_df = df_second_cycle.iloc[: max_voltage_index + 1]
    descending_df = df_second_cycle.iloc[max_voltage_index:]
    descending_df = descending_df.iloc[::-1]

    area_ascending = trapezoid(ascending_df["Im_mod"], ascending_df["Vf"])
    area_descending = trapezoid(descending_df["Im_mod"], descending_df["Vf"])
    enclosed_area = abs(area_ascending - area_descending)
    capacitance = enclosed_area
    return capacitance


def calc_bleach_charge(bleach_file):
    df = pd.read_csv(
        bleach_file,
        sep=" ",
        header=None,
        names=[
            "Time",
            "Vf",
            "Vu",
            "Im",
            "Q",
            "Vsig",
            "Ach",
            "IERange",
            "Over",
            "StopTest",
        ],
    )
    df_copy = df.copy()
    df_copy["Im"] = df_copy["Im"].apply(modify_function)
    bleach_charge = abs(trapezoid(df_copy["Im"], df_copy["Time"]))
    return bleach_charge


def calc_dep_eff(charge, capacitance):
    dep_eff = charge / capacitance
    return dep_eff


def calc_echromic_eff(bleach_charge, deltaE00):
    echromic_eff = deltaE00 / bleach_charge
    return echromic_eff


def get_expID(filename):
    match = re.search(r"_([0-9]{8})_", filename)
    if match:
        return match.group(1)
    else:
        return None


def process_metrics(metrics_df: RawMetrics, input_df: MLInput) -> PEDOTMetrics:
    deltaE00 = metrics_df.Delta_E00
    files_by_experiment_ID = {}
    results = []

    deposition_file = input_df.CA_deposition
    CV_file = input_df.CV_characterization
    bleach_file = input_df.CA_bleaching

    try:
        charge = None
        capacitance = None
        bleach_charge = None

        try:
            charge = calc_charge(deposition_file)
        except Exception as e:
            print(
                f"Error calculating charge for experiment_ID {input_df.experiment_id}: {e}"
            )

        try:
            capacitance = calc_capacitance(CV_file)
        except Exception as e:
            print(
                f"Error calculating capacitance for experiment_ID {input_df.experiment_id}: {e}"
            )

        try:
            bleach_charge = calc_bleach_charge(bleach_file)
        except Exception as e:
            print(
                f"Error calculating bleach charge for experiment_ID {input_df.experiment_id}: {e}"
            )

        if charge is not None and capacitance is not None and bleach_charge is not None:
            dep_eff = calc_dep_eff(charge, capacitance)
            echromic_eff = calc_echromic_eff(bleach_charge, deltaE00)

            calculated_metrics = PEDOTMetrics(
                experiment_id=input_df.experiment_id,
                DepositionChargePassed=charge,
                BleachChargePassed=bleach_charge,
                Capacitance=capacitance,
                DepositionEfficiency=dep_eff,
                ElectrochromicEfficiency=echromic_eff,
            )
            results.append(
                {
                    "experiment_ID": input_df.experiment_id,
                    "DepositionChargePassed": charge,
                    "BleachChargePassed": bleach_charge,
                    "Capacitance": capacitance,
                    "DepositionEfficiency": dep_eff,
                    "ElectrochromicEfficiency": echromic_eff,
                }
            )
            print(f"Processed experiment_ID: {input_df.experiment_id}")
        else:
            print(
                f"Processing incomplete for experiment_ID {input_df.experiment_id} due to earlier errors."
            )

    except Exception as e:
        print(f"Unexpected error for experiment_ID {input_df.experiment_id}: {e}")

    # Convert results to a dataframe and save to a csv
    results_df = pd.DataFrame(results)
    return calculated_metrics
