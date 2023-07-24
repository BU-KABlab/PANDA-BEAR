'''
To test the reading in of parameters and turning them into obejcts and instructions
'''
import read_json
import classes

def read_instructions(filename):
    instructions = []
    parameters = read_json.read_json(filename)
    for experiment in range(len(parameters['Experiments'])):
        instructions.append(parameters['Experiments'][experiment])
    return instructions
    
def read_vials(filename):    
    vial_parameters = read_json.read_json(filename)
    
    sol_objects = {}
    for key, values in vial_parameters.items():
        for items in values: 
            sol_objects[items['solution']] = classes.Vial(x=items['x'], 
                                                          y=items['y'],
                                                          volume=items['StartingVolume'],
                                                          name=items['name'],
                                                          contents=items['contents']
                                                          )
    return sol_objects

def read_waste_vials(filename):    
    sol_objects = {}
    waste_vials = read_json.read_json(filename)
    for key, values in waste_vials.items():
        for items in values: 
            sol_objects[items['solution']] = classes.Vial(x=items['x'], 
                                                          y=items['y'],
                                                          volume=items['StartingVolume'],
                                                          name=items['name'],
                                                          contents=items['contents']
                                                          )
            

    return waste_vials


def main():

    instructions = read_instructions('experimentParameters_07_24_23.json')
    sol_objects = read_vials('vialParameters_07_24_23.json')
    waste_vials = read_waste_vials('wasteVials_07_24_23.json')
    return instructions, sol_objects, waste_vials

if __name__ == '__main__':
    instructions, sol_objects, waste_vials = main()

    print(instructions)
    print()
    print(sol_objects)
    print()
    print(waste_vials)
