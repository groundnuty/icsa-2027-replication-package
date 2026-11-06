
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040101.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
print(f"Lat range: {lat[0]} to {lat[-1]}, step ~ {lat[1]-lat[0]}")
print(f"Lon range: {lon[0]} to {lon[-1]}, step ~ {lon[1]-lon[0]}")

# Region: lat 54.17-55.37, lon 13.25-14.45
lat_sel = (lat >= 54.17) & (lat <= 55.37)
lon_sel = (lon >= 13.25) & (lon <= 14.45)
print(f"Lat indices: {np.where(lat_sel)[0][0]} to {np.where(lat_sel)[0][-1]}")
print(f"Lon indices: {np.where(lon_sel)[0][0]} to {np.where(lon_sel)[0][-1]}")
print(f"Lat values selected: {lat[lat_sel]}")
print(f"Lon values selected: {lon[lon_sel]}")
