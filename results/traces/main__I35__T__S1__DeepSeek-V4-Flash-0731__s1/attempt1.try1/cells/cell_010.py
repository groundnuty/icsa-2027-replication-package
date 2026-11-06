
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

f = fs.open(f'{base}/sst_20090601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Get lat and lon
lat = ds.latitude.values
lon = ds.longitude.values

# Region: lat 59.93 to 61.13, lon 18.69 to 19.89
lat_mask = (lat >= 59.93) & (lat <= 61.13)
lon_mask = (lon >= 18.69) & (lon <= 19.89)

lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"Lat indices: {lat_idx}, values: {lat[lat_idx]}")
print(f"Lon indices: {lon_idx}, values: {lon[lon_idx]}")
print(f"Number of lat cells: {len(lat_idx)}, lon cells: {len(lon_idx)}")

# Check SST values in region
sst = ds.analysed_sst.values[0]
print(f"\nSST in region (shape {len(lat_idx)}x{len(lon_idx)}):")
print(sst[np.ix_(lat_idx, lon_idx)])
print(f"\nNaN values: {np.isnan(sst[np.ix_(lat_idx, lon_idx)]).sum()}")
