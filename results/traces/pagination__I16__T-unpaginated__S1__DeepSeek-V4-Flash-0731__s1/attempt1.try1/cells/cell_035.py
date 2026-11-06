
import fsspec
import xarray as xr
import numpy as np
import os

# Read exact coordinates from dataset
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat_full = ds['latitude'].values
lon_full = ds['longitude'].values

# Region indices
lat_idx = np.arange(157, 217)
lon_idx = np.arange(562, 622)
region_lat_exact = lat_full[lat_idx].copy()
region_lon_exact = lon_full[lon_idx].copy()

# Current output coordinates
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
out_lat = ds_out['lat'].values
out_lon = ds_out['lon'].values

# Compare
lat_match = np.all(out_lat == region_lat_exact)
lon_match = np.all(out_lon == region_lon_exact)
print(f'Lat coordinates match: {lat_match}')
print(f'Lon coordinates match: {lon_match}')

if not lat_match:
    diff = np.where(out_lat != region_lat_exact)[0]
    print(f'Lat mismatches at indices {diff}')
    for i in diff[:5]:
        print(f'  idx {i}: output={out_lat[i]}, dataset={region_lat_exact[i]}, diff={out_lat[i]-region_lat_exact[i]}')

if not lon_match:
    diff = np.where(out_lon != region_lon_exact)[0]
    print(f'Lon mismatches at indices {diff}')
    for i in diff[:5]:
        print(f'  idx {i}: output={out_lon[i]}, dataset={region_lon_exact[i]}, diff={out_lon[i]-region_lon_exact[i]}')

# Check exact float32 representation
print('\nComparing exact float32 representations:')
for i in [0, 5, 30, 59]:
    out_val = out_lat[i]
    ds_val = region_lat_exact[i]
    print(f'  lat[{i}]: output={out_val!r}, dataset={ds_val!r}, match={out_val == ds_val}')

for i in [0, 5, 30, 59]:
    out_val = out_lon[i]
    ds_val = region_lon_exact[i]
    print(f'  lon[{i}]: output={out_val!r}, dataset={ds_val!r}, match={out_val == ds_val}')
