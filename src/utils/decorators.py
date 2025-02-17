import functools
import pandas as pd

def validate_expiration(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if pd.isna(result) or not isinstance(result, pd.Timestamp):
            raise ValueError("Invalid expiration date")
        return result
    return wrapper 