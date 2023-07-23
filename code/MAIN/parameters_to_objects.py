'''
To test the reading in of parameters and turning them into obejcts and instructions
'''
import read_json
import classes

def main():
    '''test code'''
    instructions = []
    parameters = read_json.read_json('experimentParameters_07_22_23.json')
    for experiment in range(len(parameters['Experiments'])):
        instructions.append(parameters['Experiments'][experiment])
    print(instructions)
    vial_parameters = read_json.read_json('vialParameters_07_22_23.json')
    
    sol_objects = {}
    for key, values in vial_parameters.items():
        for items in values: 
            sol_objects[items['solution']] = classes.Vial(x=items['x'], 
                                                          y=items['y'],
                                                          volume=items['StartingVolume'],
                                                          name=items['name'],
                                                          contents=items['contents']
                                                          )
    print(sol_objects)

if __name__ == '__main__':
    main()
