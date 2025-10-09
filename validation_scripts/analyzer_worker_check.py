import multiprocessing
from multiprocessing import Queue

from panda_lib.experiment_analysis_loop import analysis_worker

if __name__ == "__main__":
    status_queue = Queue()
    analysis_process = multiprocessing.Process(
        target=analysis_worker,
        args=(status_queue, 1, False),
    )
    analysis_process.start()
    while True:
        print(status_queue.get())
        if not analysis_process.is_alive():
            break
    analysis_process.join()
    print("Analysis process finished")
