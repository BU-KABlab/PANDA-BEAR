from time import sleep
from tqdm import tqdm

def delay_timer(seconds: int) -> None:
    """
    Delay the execution for a specified number of seconds.

    Args:
        seconds (int): The number of seconds to delay.

    Returns:
        None
    """
    for _ in tqdm(range(seconds), desc="Pausing", unit="s"):
        sleep(1)


if __name__ ==  "__main__":
    delay_timer(5)