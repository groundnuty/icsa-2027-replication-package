
import xarray as xr
import numpy as np
from datetime import date, timedelta

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

# Day-of-year mapping
def doy_from_month_day(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Load extended baseline data
ext_base_start = np.datetime64('1991-12-27')
ext_base_end = np.datetime64('2003-01-05')
ext_base_mask = (time >= ext_base_start) & (time <= ext_base_end)
ext_base_time_idx = np.where(ext_base_mask)[0]
ext_base_time = time[ext_base_time_idx]

print("Loading extended baseline data...")
ext_data = ds.analysed_sst.isel(time=ext_base_time_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
print("Loaded ext_data shape:", ext_data.shape)

# Map each time to a date object
def npdt_to_date(t):
    return date(t.astype('datetime64[D]').astype(object).year, 
                t.astype('datetime64[D]').astype(object).month,
                t.astype('datetime64[D]').astype(object).day)

ext_dates = [npdt_to_date(t) for t in ext_base_time]
print("First few ext dates:", ext_dates[:5], "last:", ext_dates[-1])
