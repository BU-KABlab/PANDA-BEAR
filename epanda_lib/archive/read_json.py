'''
Reads a JSON file and returns the data as a dictionary.
:param filename: The name of the JSON file to read.
:return: The data from the JSON file as a dictionary.
'''
import json
import pathlib



def read_json(filename: str):
    '''
    Reads a JSON file and returns the data as a dictionary.
    :param filename: The name of the JSON file to read.
    :return: The data from the JSON file as a dictionary.
    '''
    cwd = pathlib.Path(__file__).parents[1]
    file_path = cwd / "instructions"
    file_to_open = file_path / filename
    with open(file_to_open, 'r',encoding = 'ascii') as file:
        data = json.load(file)
    return data

if __name__ == '__main__':
    instructions = []
    parameters = read_json('experimentParameters_07_22_23.json')
    for experiment in range(len(parameters['Experiments'])):
        instructions.append(parameters['Experiments'][experiment])

    for value in instructions:
        print(value)
