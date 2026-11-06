
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds['analysed_sst'])
print(ds['time'].values[:5], ds['time'].values[-5:])
print(len(ds['time']))
print(ds['latitude'].values[:5], ds['latitude'].values[-5:])
print(ds['longitude'].values[:5], ds['longitude'].values[-5:])
