import numpy as np
import datetime as dt
import pandas as pd
import xarray as xr

target_ds = xr.open_dataset('/tmp/target_data.nc')
target_time = target_ds['time'].values
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

expected_start = dt.date(2004, 6, 1)
expected_end = dt.date(2004, 8, 31)
expected_dates = []
d = expected_start
while d <= expected_end:
    expected_dates.append(d)
    d += dt.timedelta(days=1)

print(f"Expected: {len(expected_dates)}, Actual: {len(target_dates)}")
missing = set(expected_dates) - set(target_dates)
print(f"Missing: {len(missing)}")
