import numpy as np
import datetime as dt
import pandas as pd
import xarray as xr

# Load base dates
base_ds = xr.open_dataset('/tmp/base_data.nc')
base_time = base_ds['time'].values
base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]

# Check for gaps in the base data
expected_start = dt.date(1991, 12, 27)
expected_end = dt.date(2003, 1, 5)
expected_dates = []
d = expected_start
while d <= expected_end:
    expected_dates.append(d)
    d += dt.timedelta(days=1)

print(f"Expected dates: {len(expected_dates)}")
print(f"Actual dates: {len(base_dates)}")
print(f"First: {base_dates[0]}, Last: {base_dates[-1]}")

# Check for missing dates
missing = set(expected_dates) - set(base_dates)
print(f"Missing dates: {len(missing)}")
if missing:
    print("First few missing:", sorted(missing)[:10])
    print("Last few missing:", sorted(missing)[-10:])

# Check for extra dates
extra = set(base_dates) - set(expected_dates)
print(f"Extra dates: {len(extra)}")
