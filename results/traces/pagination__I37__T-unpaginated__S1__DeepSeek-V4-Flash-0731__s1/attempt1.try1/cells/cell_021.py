
import fsspec
import xarray as xr
import numpy as np
import datetime
import pickle

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Region
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Get region indices
f = fs.open(f'{base}/sst_20120601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_idx_arr = np.where((lats >= lat_min) & (lats <= lat_max))[0]
lon_idx_arr = np.where((lons >= lon_min) & (lons <= lon_max))[0]
lat_idx = slice(lat_idx_arr[0], lat_idx_arr[-1]+1)
lon_idx = slice(lon_idx_arr[0], lon_idx_arr[-1]+1)
region_lats = lats[lat_idx]
region_lons = lons[lon_idx]
ds.close()
f.close()

# Target dates
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

print(f"Target dates: {len(target_dates)} days")

# Read target data
print("Reading target data...")
n_target = len(target_dates)
n_lat = len(lat_idx_arr)
n_lon = len(lon_idx_arr)
target_sst = np.full((n_target, n_lat, n_lon), np.nan, dtype=np.float64)

for i, date in enumerate(target_dates):
    fname = f'sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc'
    f = fs.open(f'{base}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    target_sst[i] = ds.analysed_sst.values[0, lat_idx, lon_idx]
    ds.close()
    f.close()

print(f"Target SST shape: {target_sst.shape}")
print(f"NaN fraction: {np.isnan(target_sst).mean():.4f}")

# Determine sea cells: cells with finite SST on every day of target period
sea_mask = ~np.isnan(target_sst).any(axis=0)  # (n_lat, n_lon)
print(f"Sea cells: {sea_mask.sum()} / {n_lat * n_lon}")

np.save('work/target_sst.npy', target_sst)
np.save('work/sea_mask.npy', sea_mask)
print("Saved target data")
