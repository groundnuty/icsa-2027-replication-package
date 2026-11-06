
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import time

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544

# Quick check: load a few target files and a few baseline files
# to verify the data and understand the temperature ranges

# Check target data for a specific cell
f = fs.open(f'{base_path}/sst_20170601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()
print("Target 2017-06-01, cell (0,0):", sst[0,0])
print("Target 2017-06-01, cell (30,30):", sst[30,30])

# Check a baseline summer date
f = fs.open(f'{base_path}/sst_19950701.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst2 = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()
print("\nBaseline 1995-07-01, cell (0,0):", sst2[0,0])
print("Baseline 1995-07-01, cell (30,30):", sst2[30,30])

# Check a few more baseline summer dates
for fname in ['19920601', '19960615', '20000715', '20020801']:
    f = fs.open(f'{base_path}/sst_{fname}.nc', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    s = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
    ds.close()
    print(f"Baseline {fname}, cell (0,0): {s[0,0]:.2f}, cell (30,30): {s[30,30]:.2f}")

# Check NaN pattern in target
f = fs.open(f'{base_path}/sst_20170601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()
print("\nTarget NaN mask for 2017-06-01:")
print(sst[0,:5])
print(sst[30,30])
