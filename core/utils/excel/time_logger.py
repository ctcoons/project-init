from functools import wraps
import time


def log_speed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()  # high-resolution timer
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f"[SPEED] Function '{func.__name__}' took {elapsed:.6f} seconds")
        return result
    return wrapper