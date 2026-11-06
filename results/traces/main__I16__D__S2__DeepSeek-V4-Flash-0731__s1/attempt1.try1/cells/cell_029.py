
import numpy as np
import xarray as xr
from datetime import date, timedelta

def day_of_year(month, day):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Load smoothed thresholds and climatologies
threshold_smooth = np.load('/work/threshold_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')

# Load target data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_idx = np.where((lon >= 20.23) & (lon <= 21.43))[0]
time = ds.time.values
t_start = np.where(time >= np.datetime64('2008-06-01'))[0][0]
t_end = np.where(time <= np.datetime64('2008-08-31'))[0][-1]

target_region = ds['analysed_sst'].isel(time=slice(t_start, t_end+1),
                                        latitude=lat_idx, longitude=lon_idx).load()
target_times = target_region.time.values
n_target = len(target_times)

# Get doy for each target date
target_dates = [date(1970,1,1) + timedelta(days=int((t - np.datetime64('1970-01-01')) / np.timedelta64(1,'D'))) 
                for t in target_times]
target_doys = np.array([day_of_year(d.month, d.day) for d in target_dates])
print("Target dates:", target_dates[0], "to", target_dates[-1])
print("Target doys:", target_doys[0], "to", target_doys[-1])

# SST data for target
target_data = target_region.values.astype(np.float64)  # (92, 60, 60)

# Sea mask
sea_mask = np.all(np.isfinite(target_data), axis=0)  # (60, 60)

# For each target day, get threshold for that doy
# threshold_smooth is (366, 60, 60)
thresh_for_target = threshold_smooth[target_doys - 1]  # (92, 60, 60)

# Hot days: SST >= threshold, for sea cells only
hot = np.zeros_like(target_data, dtype=bool)
hot[:, sea_mask] = target_data[:, sea_mask] >= thresh_for_target[:, sea_mask]

print("Number of hot cell-days:", np.sum(hot))
print("Hot day counts per cell:", np.sum(hot, axis=0).min(), "to", np.sum(hot, axis=0).max())
