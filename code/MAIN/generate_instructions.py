import csv
from classes import Vial


def instruction_reader(filename: str, solution: object,rows:str,cols:int):
    ROWS = rows
    COLS = cols
    
    instructions=[]
    file_path = 'code/instructions/'+filename
    with open(file_path, newline='') as file:
        reader = csv.reader(file,delimiter = ',')

        for letter,row in zip(ROWS,reader):
            for i, amount in zip(range(1,COLS), row):
                #print(f'{letter}{i}: {amount}, ',end = '')
                well = letter + str(i)
                instructions.append(
                    {'Target Well': well, 'Solution': solution,'Pipette Volume': amount, 'Test Type': 'Test','Test duration': 10}
                )
            #print()  

    return instructions

def main():
    ROWS = 'ABCDEFGH'
    COLS = 13

    sol1 = Vial( 0,  -84, "Red", 20)
    sol2 = Vial( 0, -115, "Blue", 20)
    sol3 = Vial( 0, -150, "water", 20)


    instructions = []

    # solution 1
    instructions += instruction_reader('sol1.csv',sol1,ROWS,COLS)

    # solution 2
    instructions += instruction_reader('sol2.csv',sol1,ROWS,COLS)

    # solution 3
    instructions += instruction_reader('sol3.csv',sol1,ROWS,COLS)

    for set in instructions:
        print(set)


if __name__ == "__main__":
    main()
    