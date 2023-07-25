import time

def record_time_step(well: str, step: str, run_times: dict):
    currentTime = time.time()
    sub_key = step + ' Time'
    if well not in run_times:
        run_times[well] = {}
        run_times[well][sub_key] = currentTime
    else:
        run_times[well][sub_key] = currentTime - run_times[well][list(run_times[wellRun])[-1]]
    print(f'{step} time: {run_times[well][sub_key]}')


RunTimes = {}
wellRun = 'A1'

record_time_step(wellRun, 'Start', RunTimes)
time.sleep(1)
record_time_step(wellRun, 'Initializing', RunTimes)
time.sleep(1)
record_time_step(wellRun, 'Pipetting', RunTimes)
time.sleep(1)
record_time_step(wellRun, 'End', RunTimes)
time.sleep(1)

print(RunTimes)