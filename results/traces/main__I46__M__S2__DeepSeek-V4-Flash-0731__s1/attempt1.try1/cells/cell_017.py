
import xarray as xr
import numpy as np
from datetime import date

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

# Load threshold and climatology
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

# Day-of-year mapping
def doy_from_month_day(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Load target data
target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_time = time[target_time_idx]
target_data = ds.analysed_sst.isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

print("Target data shape:", target_data.shape)
print("Target days:", len(target_time_idx))

# Get day of year for each target day
target_doy = []
for t in target_time:
    dt = t.astype('datetime64[D]').astype(object)
    target_doy.append(doy_from_month_day(dt.month, dt.day))

print("Target doys:", target_doy[0], "to", target_doy[-1])

# Sea cells mask
sea_mask = ~np.isnan(target_data).any(axis=0)
print("Sea cells:", sea_mask.sum())

# For each sea cell, determine if each day is hot
# Hot if SST >= threshold for that day of year
n_target = len(target_time_idx)
n_lat, n_lon = 60, 60

# Initialize hot array
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for t_idx in range(n_target):
    doy = target_doy[t_idx]
    thr = threshold_smooth[doy - 1, :, :]
    # Only check sea cells
    sst = target_data[t_idx, :, :]
    hot[t_idx] = (sst >= thr) & sea_mask

print("Hot cells:", hot.sum())
print("Hot array shape:", hot.shape)

# Check if sea cells have NaN SST in target period (shouldn't by definition)
print("NaN in target data for sea cells:", np.isnan(target_data[:, sea_mask]).sum())

# Save hot array
np.save('/tmp/hot.npy', hot)
np.save('/tmp/sea_mask.npy', sea_mask)
np.save('/tmp/target_doy.npy', np.array(target_doy))
print("Saved hot array")
