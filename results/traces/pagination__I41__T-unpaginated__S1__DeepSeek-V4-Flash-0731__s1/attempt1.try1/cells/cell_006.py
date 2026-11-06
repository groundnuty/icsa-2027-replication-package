
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check data values for one file
f = fs.open(f'{base}/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 61.57) & (lat <= 62.77))[0]
lon_idx = np.where((lon >= 20.17) & (lon <= 21.37))[0]

region_sst = ds.analysed_sst.values[0, lat_idx.min():lat_idx.max()+1, lon_idx.min():lon_idx.max()+1]
print("Region SST shape:", region_sst.shape)
print("Some values:", region_sst[:3, :3])
print("NaN count:", np.isnan(region_sst).sum())
print("Total:", region_sst.size)
