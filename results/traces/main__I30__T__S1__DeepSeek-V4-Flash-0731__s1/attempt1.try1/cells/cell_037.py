
import numpy as np
import xarray as xr
import pandas as pd

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds['mhw'].values
times = pd.to_datetime(ds['time'].values)

active = np.any(mhw > 0, axis=(1, 2))
active_days = np.where(active)[0]

print("Active day indices:", active_days[0], "to", active_days[-1], "count:", len(active_days))
print("All consecutive:", np.all(np.diff(active_days) == 1))

print("First active day:", times[active_days[0]].strftime('%Y-%m-%d'))
print("Last active day:", times[active_days[-1]].strftime('%Y-%m-%d'))

# Check days before and after
if active_days[0] > 0:
    print(f"Day before first active ({times[active_days[0]-1].strftime('%Y-%m-%d')}): active={active[active_days[0]-1]}")
if active_days[-1] < len(active) - 1:
    print(f"Day after last active ({times[active_days[-1]+1].strftime('%Y-%m-%d')}): active={active[active_days[-1]+1]}")
