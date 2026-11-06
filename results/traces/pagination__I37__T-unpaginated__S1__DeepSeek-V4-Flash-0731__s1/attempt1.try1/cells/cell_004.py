
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

f = fs.open(f'{base}/sst_20120601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lats = ds.latitude.values
lons = ds.longitude.values
print("Lat range:", lats[0], lats[-1], "step:", lats[1]-lats[0])
print("Lon range:", lons[0], lons[-1], "step:", lons[1]-lons[0])

# Region: lat 60.09-61.29, lon 20.01-21.21
lat_mask = (lats >= 60.09) & (lats <= 61.29)
lon_mask = (lons >= 20.01) & (lons <= 21.21)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
print("Lat values:", lats[lat_idx])
print("Lon values:", lons[lon_idx])

# Check SST values
sst = ds.analysed_sst.values
print("SST shape:", sst.shape)
print("SST min/max:", np.nanmin(sst), np.nanmax(sst))
print("SST dtype:", sst.dtype)

# Check if there's a land mask (NaN for land?)
region = sst[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
print("Region SST sample:", region)
print("Region shape:", region.shape)
