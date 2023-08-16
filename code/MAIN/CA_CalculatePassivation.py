from http import HTTPStatus
import os
import numpy as np
import pandas as pd
import pathlib

def calcpass(file_path, echem_function, search_values):
    calculated_results = []  # List to store calculated values
    file_names = []  # List to store file names

    for search_value1, search_value2 in search_values:
        df = pd.read_csv(file_path, 
                         sep=" ", 
                         header=None, 
                         names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

        row_index1 = df[df['Time'] == search_value1].index[0]
        value1 = df.loc[row_index1, 'Im']

        row_index2 = df[df['Time'] == search_value2].index[0]
        value2 = df.loc[row_index2, 'Im']

        result = value1 / value2

        calculated_results.append(result)
        file_names.append(file_path.name)  # Store file name

    return calculated_results, file_names

def calculate_and_save(folder_path, echem_function, search_values):
    results = []
    file_names = []

    for file_path in folder_path.glob("*_dep.txt"):
        calc_results, names = calcpass(file_path, echem_function, search_values)
        results.extend(calc_results)
        file_names.extend(names)

    result_df = pd.DataFrame({"File Name": file_names, "Result": results})
    return result_df

folder_path = pathlib.Path(__file__).parents[2] /  "data" / "2023-08-08"
echem_function = "dep"
search_values = [(300,3)]  # List of tuples with search value pairs

result_dataframe = calculate_and_save(folder_path, echem_function, search_values)
print(result_dataframe)
result_dataframe.to_csv("result_dataframe.csv", index=False)
