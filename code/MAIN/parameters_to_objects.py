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

    vial_parameters = read_json.read_json('vialParameters_07_22_23.json')
    sol_objects = {}
    for key, values in vial_parameters.items():
        if key.startswith('sol'):
            sol_objects[key] = classes.Vial(x=values['x'], y=values['y'], volume=values['volume'], name=values['name'], contents=values['contents'])
            

if __name__ == '__main__':
    main()
