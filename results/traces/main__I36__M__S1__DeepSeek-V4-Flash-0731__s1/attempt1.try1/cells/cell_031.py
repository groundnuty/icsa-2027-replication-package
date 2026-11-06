
import os
import numpy as np
from datetime import date
import json

# Load data
cell_mhw = np.load('/tmp/cell_mhw.npy')
with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
target_dates = [date.fromisoformat(s) for s in target_dates_str]

# Load region coordinates
import h5py
base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
with h5py.File(os.path.join(base_dir, 'sst_20030601.nc'), 'r') as h5:
    lat = h5['latitude'][:]
    lon = h5['longitude'][:]
lat_idx = np.where((lat >= 60.09) & (lat <= 61.29))[0]
lon_idx = np.where((lon >= 20.01) & (lon <= 21.21))[0]
lat_region = lat[lat_idx]
lon_region = lon[lon_idx]

# Create output directory
os.makedirs('output', exist_ok=True)

# Create mhw_mask.nc
import xarray as xr

# mhw: (time, lat, lon) uint8
mhw = cell_mhw.astype(np.uint8)  # 1 where in per-cell MHW, 0 otherwise

# Create dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'latitude', 'longitude'), mhw)
    },
    coords={
        'time': np.array(target_dates, dtype='datetime64[ns]'),
        'latitude': lat_region,
        'longitude': lon_region,
    }
)

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")
print(f"Shape: {ds_out.mhw.shape}")
print(f"Dtype: {ds_out.mhw.dtype}")

# Verify
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Verify - shape: {ds_check.mhw.shape}")
print(f"Verify - dtype: {ds_check.mhw.dtype}")
print(f"Verify - time: {ds_check.time.values[:3]} ... {ds_check.time.values[-3:]}")
print(f"Verify - mhw sum: {ds_check.mhw.values.sum()}")
ds_check.close()
