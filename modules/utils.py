import time
from requests.exceptions import ConnectionError, JSONDecodeError

def retry_on_connection_error(func):
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except (ConnectionError, JSONDecodeError):
                print(f"Connection error detected in {func.__name__}. Retrying...")
            time.sleep(2)
    return wrapper
