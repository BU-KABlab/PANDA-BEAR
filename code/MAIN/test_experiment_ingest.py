import json, pathlib, datetime

def check_well_status(well: str):
    """
    Checks the status of a well.
    :param well: The well to check.
    :return: The status of the well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for well in data['Wells']:
            if well['Target_Well'] == well:
                return well['status']

def choose_alternative_well(well: str):
    """
    Chooses an alternative well if the target well is not available.
    :param well: The well to check.
    :return: The alternative well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for well in data['Wells']:
            if well['status'] == "new":
                return well['Target_Well']
        return "none"    

def change_well_status(well: str, status: str):
    """
    Changes the status of a well.
    :param well: The well to change.
    :param status: The new status of the well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for wells in data['Wells']:
            if wells['Target_Well'] == well:
                wells['status'] = status
                wells['status_date'] = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
                break
    with open(file_to_open, "w") as file:
        json.dump(data, file, indent=4)

def read_new_experiments(filename: str):
    """
    Reads a JSON file and returns the data as a dictionary.
    :param filename: The name of the JSON file to read.
    :return: The data from the JSON file as a dictionary.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "inbox"
    file_to_open = file_path / filename
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for experiment in data['Experiments']:
            # Get the target well and create a filename
            desired_well = experiment['Target_Well']

            # Check if the well is available
            if check_well_status(desired_well) != "new":
                # Find the next available well
                target_well = choose_alternative_well(desired_well)
                if target_well == "none":
                    print(f"No wells available for experiment originally for well {desired_well}.")
                    continue
                print(f"Experiment originally for well {desired_well} is now for well {target_well}.")                
            else:
                target_well = desired_well

            filename = f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}_{target_well}.json"

            # Save the experiment as a separate file in the experiment_que subfolder
            subfolder_path = cwd / "experiment_que"
            subfolder_path.mkdir(parents=True, exist_ok=True)
            file_to_save = subfolder_path / filename
            with open(file_to_save, "w") as outfile:
                json.dump(experiment, outfile, indent=4)

            # Change the status of the well
            change_well_status(target_well, "qued")

            # Delete the experiment from the inbox
            file_to_open.unlink()

    return [experiment['Target_Well'] for experiment in data['Experiments']]

def check_inbox():
    """
    Checks the inbox for new experiments.
    :return: the filename(s) of new experiments.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "inbox"
    for file in file_path.iterdir():
        if file.is_file():
            return read_new_experiments(file.name)
        

if __name__ == "__main__":
    check_inbox()

    