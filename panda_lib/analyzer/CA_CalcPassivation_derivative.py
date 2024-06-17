from http import HTTPStatus
import os
import numpy as np
import pandas as pd
import pathlib
from scipy.interpolate import interp1d

def calcpass(file_path, echem_function, search_values):
    calculated_results = []  # List to store calculated values
    file_names = []  # List to store file names
    derivative_at_median = []  # List to store derivative at median values

    df = pd.read_csv(file_path, 
                     sep=" ", 
                     header=None, 
                     names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

    # Filter data between Time values 2 and 50 (ignore data below 2 seconds)
    df_filtered = df[df['Time'] >= 30]

    if not df_filtered.empty:
        # Calculate the maximum and minimum Im values
        max_im = np.max(df_filtered['Im'])
        min_im = np.min(df_filtered['Im'])

        # Calculate the first derivative using interpolation
        f = interp1d(df_filtered['Time'], df_filtered['Im'], kind='linear')
        derivative = np.gradient(f(df_filtered['Time']), df_filtered['Time'])

        # Calculate the derivative value at the closest time value to the median Im value
        median_im = np.median(df_filtered['Im'])
        closest_index = np.argmin(np.abs(df_filtered['Im'] - median_im))
        closest_time = df_filtered.loc[closest_index, 'Time']
        derivative_at_closest_time = f(closest_time)

        # Store the calculated results and other values
        calculated_results.append(derivative)
        file_names.append(file_path.name)  # Store file name
        derivative_at_median.append(derivative_at_closest_time)  # Store derivative at closest median value

    return calculated_results, file_names, max_im, min_im, derivative_at_median

def calculate_and_save(folder_path, echem_function, search_values):
    results = []
    file_names = []
    max_values = []
    min_values = []
    derivative_at_median_values = []

    for file_path in folder_path.glob("*_dep.txt"):
        calc_results, names, max_im, min_im, median_vals = calcpass(file_path, echem_function, search_values)
        results.extend(calc_results)
        file_names.extend(names)
        if calc_results:
            max_values.append(max_im)
            min_values.append(min_im)
            derivative_at_median_values.extend(median_vals)

    result_df = pd.DataFrame({"File Name": file_names, 
                              "Max Im": max_values,
                              "Min Im": min_values,
                              "Derivative at Closest Median Time": derivative_at_median_values})
    return result_df

folder_path = pathlib.Path(__file__).parents[2] /  "data" / "2023-08-08"
echem_function = "dep"

# Generate search values between 20 and 50
search_values = []  # No need to define search values in this case

result_dataframe = calculate_and_save(folder_path, echem_function, search_values)
print(result_dataframe)
result_dataframe.to_csv("result_dataframe.csv", index=False)
