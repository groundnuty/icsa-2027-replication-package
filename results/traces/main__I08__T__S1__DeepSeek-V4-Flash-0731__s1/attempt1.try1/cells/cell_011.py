
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Define the time indices and spatial indices we need
# Baseline: 3647-7674, Target: 9282-9373
# Lat: 66-125, Lon: 531-590

# Try reading a small slice first to test
base_start, base_end = 3647, 7674
tgt_start, tgt_end = 9282, 9373
lat_s = 66
lat_e = 125  # inclusive
lon_s = 531
lon_e = 590  # inclusive

# Read baseline data for the region
print("Reading baseline data...")
base_data = ds['analysed_sst'].isel(
    time=slice(base_start, base_end+1),
    latitude=slice(lat_s, lat_e+1),
    longitude=slice(lon_s, lon_e+1)
).values
print("Baseline data shape:", base_data.shape)
print("Baseline data dtype:", base_data.dtype)
print("Baseline data range:", np.nanmin(base_data), np.nanmax(base_data))
