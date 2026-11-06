
import xarray as xr
import numpy as np
from datetime import datetime, date, timedelta

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_idx = list(range(34, 94))
lon_idx = list(range(213, 273))

time = ds['time'].values
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time >= baseline_start) & (time <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]

# Baseline dates as Python date objects
baseline_dates = [datetime.utcfromtimestamp(int(t) / 1e9).date() for t in time[baseline_time_idx]]
print("First few baseline dates:", baseline_dates[:3])
print("Last few baseline dates:", baseline_dates[-3:])
print("Count:", len(baseline_dates))
