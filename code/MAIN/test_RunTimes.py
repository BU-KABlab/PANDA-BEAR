import time, json, pathlib

def record_time_step(well: str, step: str, run_times: dict):
    currentTime = int(time.time())
    sub_key = step + ' Time'
    if well not in run_times:
        run_times[well] = {}
        run_times[well][sub_key] = currentTime
    else:
        run_times[well][sub_key] = currentTime
    #print(f'{step} time: {run_times[well][sub_key]}')

def print_runtime_data(runtime_data: dict):
    for well, data in runtime_data.items():
        print(f"Well {well} Runtimes:")
        runtimes = []
        for section, runtime in data.items():
            minutes = runtime/60
            runtimes.append(minutes)
        

def save_runtime_data(run_times: dict, filename: str):
    '''Save the run times to a json file in code/run_times'''
    cwd = pathlib.Path(__file__).parents[1]
    file_path = cwd / "run_times"
    file_to_save = file_path / (filename + '.json')
    with open(file_to_save, 'w') as f:
        json.dump(run_times, f)

RunTimes = {}
wellRun = 'A1'

record_time_step(wellRun, 'Start', RunTimes)
time.sleep(1)
record_time_step(wellRun, 'Initializing', RunTimes)
time.sleep(3)
record_time_step(wellRun, 'Pipetting', RunTimes)
time.sleep(4)
record_time_step(wellRun, 'End', RunTimes)
time.sleep(6)

save_runtime_data(RunTimes, '2023_07_27_Experiment Timestamps')
print_runtime_data(RunTimes)