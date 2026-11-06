
import xarray as xr
import numpy as np
from datetime import date, timedelta
from collections import defaultdict

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_idx = np.where((lon >= 20.23) & (lon <= 21.43))[0]

time = ds.time.values
b_start = np.where(time >= np.datetime64('1991-12-27'))[0][0]
b_end = np.where(time <= np.datetime64('2003-01-05'))[0][-1]

baseline_region = ds['analysed_sst'].isel(time=slice(b_start, b_end+1), 
                                          latitude=lat_idx, longitude=lon_idx).load()
print("Baseline region shape:", baseline_region.shape)

base_times = baseline_region.time.values
print("Baseline time range:", base_times[0], base_times[-1])
