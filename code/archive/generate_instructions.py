import csv
from code.archive.classes import Vial
from pathlib import Path
import json

#TODO: add a way to monitor instruction_inbox and automatically generate instructions while moving files to a different folder

def instruction_reader(filename: str, solution: object,rows:str,cols:int):
    '''Reads a csv file and returns a list of instructions for the experiment.'''
    ROWS = rows
    COLS = cols
    
    instructions=[]
    cwd = Path().absolute()
    file_path = Path(cwd.parents[0].__str__() + "/KABLAB/code/instruction_inbox")
    file_to_open = file_path / filename
    with open(file_to_open, newline='') as file:
        reader = csv.reader(file,delimiter = ',')

        for letter,row in zip(ROWS,reader):
            for i, amount in zip(range(1,COLS), row):
                #print(f'{letter}{i}: {amount}, ',end = '')
                well = letter + str(i)
                instructions.append(
                    {'Target Well': well, 'Solution': solution.name,'Pipette Volume': float(amount), 'Test Type': 'Test','Test duration': 10}
                )
            
    return instructions

def experiment_writer(filename: str, instructions: list):
    '''Writes a list of instructions to a json file.'''
    cwd = Path().absolute()
    file_path = Path(cwd.parents[0].__str__() + "/KABLAB/code/MAIN/experiments")
    file_to_write = file_path / filename
    with open(file_to_write, "w") as final:
        json.dump(instructions, final)
    final.close()  

def experiment_reader(filename: str, print_data: bool):
    '''Reads a json file and prints the data.'''
    cwd = Path().absolute()
    file_path = Path(cwd.parents[0].__str__() + "/KABLAB/code/MAIN/experiments")
    file_to_read = file_path / filename
    f = open(file_to_read, "r")
    data = json.load(f)
    if print_data:
        for item in data:
            print(item)
    f.close()

def main():
    ROWS = 'ABCDEFGH'
    COLS = 13

    sol1 = Vial( 0,  -84, "Red", 20, name="sol1")
    sol2 = Vial( 0, -115, "Blue", 20,  name="sol2")
    sol3 = Vial( 0, -150, "water", 20, name="sol3")


    instructions = []

    # solution 1
    instructions += instruction_reader('sol1.csv',sol1,ROWS,COLS)

    # solution 2
    instructions += instruction_reader('sol2.csv',sol1,ROWS,COLS)

    # solution 3
    instructions += instruction_reader('sol3.csv',sol1,ROWS,COLS)

    filename = "experiement1.json"
    experiment_writer(filename, instructions)

    # for set in instructions:
    #     print(set)


if __name__ == "__main__":
    main()

    filename = "experiement1.json"
    experiment_reader(filename, True)   