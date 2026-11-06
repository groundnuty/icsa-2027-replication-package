
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values

# Check which grid points fall within the bounds
print("Lat values near 57.85:", lat[(lat >= 57.84) & (lat <= 57.86)])
print("Lat values near 59.05:", lat[(lat >= 59.04) & (lat <= 59.06)])
print("Lon values near 21.01:", lon[(lon >= 21.00) & (lon <= 21.02)])
print("Lon values near 22.21:", lon[(lon >= 22.20) & (lon <= 22.22)])

# Check grid step
print("lat step:", lat[1]-lat[0])
print("lon step:", lon[1]-lon[0])
