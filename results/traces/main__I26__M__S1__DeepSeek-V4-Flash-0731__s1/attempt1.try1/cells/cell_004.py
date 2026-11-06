
import xarray as xr
import numpy as np

# Examine one file's structure in detail
path = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20070601.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
print(ds['analysed_sst'].dims)
print(ds['analysed_sst'].values.shape)
print("lat range:", ds['latitude'].values.min(), ds['latitude'].values.max())
print("lon range:", ds['longitude'].values.min(), ds['longitude'].values.max())
print("lat step:", ds['latitude'].values[1]-ds['latitude'].values[0])
print("lon step:", ds['longitude'].values[1]-ds['longitude'].values[0])

# Find indices for our region
lat = ds['latitude'].values
lon = ds['longitude'].values
lat_mask = (lat >= 57.83) & (lat <= 59.03)
lon_mask = (lon >= 17.41) & (lon <= 18.61)
print("lat indices in region:", np.where(lat_mask)[0][:5], np.where(lat_mask)[0][-5:])
print("lon indices in region:", np.where(lon_mask)[0][:5], np.where(lon_mask)[0][-5:])
print("Num lat in region:", lat_mask.sum())
print("Num lon in region:", lon_mask.sum())

# Sample values
sst = ds['analysed_sst'].values[0]
print("Sample SST values at region:", sst[lat_mask][:, lon_mask])
print("NaN count in region:", np.isnan(sst[lat_mask][:, lon_mask]).sum())
ds.close()
