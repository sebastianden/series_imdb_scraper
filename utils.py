import logging
import time


def timeit(func):
    """
    Decorator to time execution times of decorated functions.

    Parameters
    ----------
    func: function
        Decorated function

    Returns
    -------
    wrapped: function
        Function that executes, logs and prints the execution time of the
        decorated function
    """
    def wrapped(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        logging.info(f" Execution time of {func.__name__}: {(time.time() - start)*1000:.0f} ms")
        return result
    return wrapped
