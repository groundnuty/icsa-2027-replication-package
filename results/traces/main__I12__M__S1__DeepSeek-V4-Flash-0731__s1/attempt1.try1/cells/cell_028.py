
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, json

# Get region lat/lon from original dataset
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
lats_full = ds0.latitude.values
lons_full = ds0.longitude.values
ds0.close()

lat_min, lat_max = 56.09, 57.29
lon_min, lon_max = 10.55, 11.75

lat_mask = (lats_full >= lat_min) & (lats_full <= lat_max)
lon_mask = (lons_full >= lon_min) & (lons_full <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
lat_start, lat_end = lat_idx[0], lat_idx[-1] + 1
lon_start, lon_end = lon_idx[0], lon_idx[-1] + 1

region_lats = lats_full[lat_start:lat_end]
region_lons = lons_full[lon_start:lon_end]

print(f"Region lats ({len(region_lats)}): {region_lats[0]} to {region_lats[-1]}")
print(f"Region lons ({len(region_lons)}): {region_lons[0]} to {region_lons[-1]}")

# Target dates
target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)
target_dates_str = [d.strftime('%Y-%m-%d') for d in target_dates]
print(f"Target dates: {target_dates_str[0]} to {target_dates_str[-1]} ({len(target_dates_str)} days)")

# Get time values from dataset
# Use the target data time coordinate
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
time_vals = ds.time.values
ds.close()
print(f"Time values: {time_vals}")

# Time coordinate for all 92 days - let me get from the first target file
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
t0 = ds.time.values[0]
ds.close()
print(f"Time coord: {t0}")

# For each target day, get the time value
time_coords = []
for d in target_dates:
    fname = f'sst_{d.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(os.path.join('/data/icsa2027_data_20261101T090944Z/s1z', fname), engine='h5netcdf')
    time_coords.append(ds.time.values[0])
    ds.close()

time_coords = np.array(time_coords)
print(f"Time coords: {time_coords[0]} to {time_coords[-1]} ({len(time_coords)} entries)")
