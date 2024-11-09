import sys
import time


def countdown_timer(samplerate, cycle):
    """Countdown timer for the data acquisition"""
    try:
        estimated_time = abs(samplerate * cycle)
        while estimated_time > 0:
            time.sleep(1)
            estimated_time -= 1
            minutes, seconds = divmod(estimated_time, 60)
            sys.stdout.write("\r")
            sys.stdout.write(
                f"Time remaining: {int(minutes)} minutes {round(seconds,2)} seconds"
            )
            sys.stdout.flush()
        sys.stdout.write("\n")
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    finally:
        sys.stdout.write("\n")
