import json, pathlib, datetime, os

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
                wells['status_date'] = datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
                break
    with open(file_to_open, "w") as file:
        json.dump(data, file, indent=4)

def read_new_experiments(filename: str):
    """
    Reads a JSON file and returns the data as a dictionary.
    :param filename: The name of the JSON file to read.
    :return: The data from the JSON file as a dictionary.
    """
    experiments_read = 0
    complete = True
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "experiments_inbox"
    file_to_open = file_path / filename
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for experiment in data['Experiments']:
            existing_status = experiment['status']
            if existing_status != "new":
                continue
            # Get the target well and create a filename
            desired_well = experiment['Target_Well']

            # Check if the well is available
            if check_well_status(desired_well) != "new":
                # Find the next available well
                target_well = choose_alternative_well(desired_well)
                if target_well == "none":
                    print(f"No wells available for experiment originally for well {desired_well}.")
                    complete = False
                    continue
                else:
                    print(f"Experiment originally for well {desired_well} is now for well {target_well}.")
                    experiment['Target_Well'] = target_well                
            else:
                target_well = desired_well

            filename = f"{datetime.datetime.now().strftime('%Y-%m-%d_%H')}_{target_well}.json"

            # add additional information to the experiment
            experiment['status_date'] = datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
            experiment["time_stamps"] = []
            experiment["OCP_file"] = ""
            experiment["OCP_pass"]= None
            experiment["deposition_data_file"] = ""
            experiment["deposition_plot_file"] = ""
            experiment["characterization_data_file"] = ""
            experiment["characterization_plot_file"] = ""


            # Save the experiment as a separate file in the experiment_que subfolder
            subfolder_path = cwd / "experiment_queue"
            subfolder_path.mkdir(parents=True, exist_ok=True)
            file_to_save = subfolder_path / filename
            with open(file_to_save, "w") as outfile:
                json.dump(experiment, outfile, indent=4)

            # Change the status of the well
            change_well_status(target_well, "queued")
            experiment['status'] = "queued"

            # Add the experiment to the list of experiments read
            experiments_read += 1
        
    # Save the updated file
    with open(file_to_open, "w") as file:
        json.dump(data, file, indent=4)



    return experiments_read, complete

def check_inbox():
    """
    Checks the experiments inbox folder for new experiments.
    :return: the filename(s) of new experiments.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "experiments_inbox"
    count = 0
    for file in file_path.iterdir():
        if file.is_file():
            [count,complete] = read_new_experiments(file.name)

            # Move to archive the file if it has been read
            if complete:
                archive_path = file_path / "archive"
                archive_path.mkdir(parents=True, exist_ok=True)
                file.replace(archive_path / file.name)
                print(f"File {file.name} moved to archive.")
            else:
                print(f"File {file.name} not moved to archive. Not all experiments read.")

    return count
        
def read_next_experiment_from_queue():
    """
    Reads the next experiment from the queue.
    :return: The next experiment.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_path = cwd / "experiment_queue"
    
    ## if folder is not empty pick the first file in the queue
    if os.listdir(file_path):
        file_to_open = file_path / os.listdir(file_path)[0]
        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
        return data, file_to_open
    else:
        return None, None

def save_completed_instructions(instructions: list, filename: str):
    '''Save the experiment instructions to either the completed or failed instructions folder.
        Delete the experiment from the instructions queue'''
    filename = filename.name
    cwd = pathlib.Path(__file__).parents[0]
    queue_file_path = cwd / "experiment_queue"
    completed_file_path = cwd / "experiments_completed"
    failed_file_path = cwd / "experiments_error"

    if instructions['status'] == "completed":
        file_to_save = completed_file_path / (filename)
    elif instructions['status'] == "error":
        file_to_save = failed_file_path / (filename)
    else:
        return False
        
    with open(file_to_save, "w") as f:
        json.dump(instructions, f, indent=4)
        print(f"Experiment {filename} saved to {file_to_save}.")

    os.remove(queue_file_path / (filename))
    print(f"Experiment {filename} removed from queue.")

if __name__ == "__main__":
    print(f"{check_inbox()} new experiments read.")

    # exp, filename = read_next_experiment_from_queue()
    # runtimes = {
    #     "Start Time": 1690497089,
    #     "Solutions Time": 1690497656,
    #     "Deposition Time": 1690497996,
    #     "Rinse Time": 1690499112,
    #     "Characterization Time": 1690499549,
    #     "Clear Well Time": 1690499769,
    #     "Flush Time": 1690499875,
    #     "End Time": 1690499875,
    #     "Well Time": 167104.380354881
    # }
    # exp["time_stamps"] = runtimes
    # exp['status'] = "error"
    # exp['status_date'] = datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
    # print(json.dumps(exp, indent=4))

    # save_completed_instructions(exp, filename)