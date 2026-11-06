
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

# Define region
lat_min, lat_max = 57.85, 59.05
lon_min, lon_max = 21.01, 22.21

# Load one file to get coordinates
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_mask = (lat_all >= lat_min) & (lat_all <= lat_max)
lon_mask = (lon_all >= lon_min) & (lon_all <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
region_lat = lat_all[lat_idx]
region_lon = lon_all[lon_idx]
nlat, nlon = len(lat_idx), len(lon_idx)
print(f"Region: {nlat} lats x {nlon} lons")

# Target period
target_start = date(2013, 6, 1)
target_end = date(2013, 8, 31)

# Load target data
target_dates = []
target_sst = []
d = target_start
while d <= target_end:
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    if not os.path.exists(fname):
        print(f"Missing file: {fname}")
        break
    ds = xr.open_dataset(fname, engine='h5netcdf')
    sst_region = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    target_sst.append(sst_region)
    target_dates.append(d)
    ds.close()
    d += timedelta(days=1)

target_sst = np.array(target_sst)
target_dates = np.array(target_dates)
print(f"Target data shape: {target_sst.shape}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}, count: {len(target_dates)}")

# Identify sea cells (finite on all target days)
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_mask.sum()} out of {nlat*nlon}")
print("Sea mask shape:", sea_mask.shape)
