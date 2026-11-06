
import xarray as xr
import fsspec
import numpy as np
import time

fs = fsspec.filesystem('onedata')

# Open s2z file
start = time.time()
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(f"Opened dataset in {time.time()-start:.2f}s")

# Select region
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

# Select time range for baseline
baseline_start = '1991-12-27'
baseline_end = '2003-01-05'
target_start = '2008-06-01'
target_end = '2008-08-31'

region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print(f"Region selection done in {time.time()-start:.2f}s")

# Load baseline data
baseline = region.sel(time=slice(baseline_start, baseline_end))
print(f"Baseline shape: {baseline.analysed_sst.shape}")
start2 = time.time()
baseline_data = baseline.analysed_sst.values
print(f"Loaded baseline in {time.time()-start2:.2f}s, shape={baseline_data.shape}, dtype={baseline_data.dtype}")

# Load target data
target = region.sel(time=slice(target_start, target_end))
start3 = time.time()
target_data = target.analysed_sst.values
print(f"Loaded target in {time.time()-start3:.2f}s, shape={target_data.shape}, dtype={target_data.dtype}")

print(f"Total time: {time.time()-start:.2f}s")
