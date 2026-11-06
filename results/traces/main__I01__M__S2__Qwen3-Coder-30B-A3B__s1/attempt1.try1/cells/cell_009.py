import numpy as np
from datetime import datetime

# Test different ways to convert numpy datetime64 to datetime
dt64 = np.datetime64('2008-06-01T00:00:00.000000000')

print("Original datetime64:", dt64)
print("Type:", type(dt64))

# Method 1: Using pd.Timestamp (if pandas is available)
try:
    import pandas as pd
    dt = pd.Timestamp(dt64).to_pydatetime()
    print("Method 1 (pandas):", dt, type(dt))
except:
    print("Method 1 failed")

# Method 2: Direct conversion using numpy's datetime64 conversion
try:
    # This is the right way:
    dt = dt64.astype('datetime64[s]').astype(datetime)
    print("Method 2 (numpy):", dt, type(dt))
except Exception as e:
    print("Method 2 failed:", e)

# Method 3: Manual conversion
try:
    # Get the number of seconds since epoch
    seconds = (dt64 - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's')
    dt = datetime.fromtimestamp(seconds)
    print("Method 3 (manual):", dt, type(dt))
except Exception as e:
    print("Method 3 failed:", e)

# Let's try the simplest approach:
def simple_day_of_year(date_obj):
    """Simple conversion to day of year"""
    if isinstance(date_obj, np.datetime64):
        # Convert to datetime via pandas if possible, or manually
        try:
            import pandas as pd
            dt = pd.Timestamp(date_obj).to_pydatetime()
        except:
            # Fallback to manual conversion
            # Convert to seconds since epoch
            seconds = (date_obj - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's')
            dt = datetime.fromtimestamp(seconds)
    else:
        dt = date_obj
    
    # Handle leap years properly
    if dt.month == 2 and dt.day == 29:
        return 60
    # Create a date for Jan 1 of the same year to calculate DOY
    jan1 = datetime(dt.year, 1, 1)
    return (dt - jan1).days + 1

# Test it
dt64 = np.datetime64('2008-06-01T00:00:00.000000000')
print("Testing simple function:")
doy = simple_day_of_year(dt64)
print(f"DOY for 2008-06-01: {doy}")