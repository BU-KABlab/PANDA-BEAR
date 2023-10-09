'''
To test the reading in of parameters and turning them into obejcts and instructions
'''
import read_json
import json
import code.archive.classes as classes
import pathlib
import time

def read_instructions(filename):
    instructions = []
    parameters = read_json.read_json(filename)
    for experiment in range(len(parameters['Experiments'])):
        instructions.append(parameters['Experiments'][experiment])
        instructions[experiment]['status'] = 'qued'
        
    return instructions
    
def read_vials(filename):    
    vial_parameters = read_json.read_json(filename)
    
    sol_objects = []
    for key, values in vial_parameters.items():
        for items in values: 
            sol_objects.append(classes.Vial(x=items['x'], 
                                                          y=items['y'],
                                                          volume=items['StartingVolume'],
                                                          name=items['name'],
                                                          contents=items['contents']
                                                          ))
    return sol_objects


def main():

    instructions = read_instructions('experimentParameters_07_24_23.json')
    sol_objects = read_vials('vialParameters_07_24_23.json')
    waste_vials = read_vials('wasteParameters_07_24_23.json')
    return instructions, sol_objects, waste_vials

if __name__ == '__main__':
    instructions, sol_objects, waste_vials = main()

    for i in range(len(instructions)): #loop per well
        wellRun = instructions[i]['Target_Well']
        ## Deposit all experiment solutions into well
        experiment_solutions = ['Acrylate', 'PEG']
        for solution in experiment_solutions:
            print(f'Pipette {instructions[i][solution]} ml of {solution} into {wellRun}')


    month = time.strftime("%m")
    day = time.strftime("%d")
    year = time.strftime("%y")
    filename = 'experiments_' + year + "_" + month + "_" + day + '.json'
    cwd = pathlib.Path(__file__).parents[1]
    file_path = cwd / "instructions"
    file_folder = file_path / (year + "_" + month + "_" + day)
    pathlib.Path(file_folder).mkdir(parents=True, exist_ok=True)
    file_to_save = file_folder / filename
    with open(file_to_save, 'w') as file:
        json.dump(instructions, file, indent=4)