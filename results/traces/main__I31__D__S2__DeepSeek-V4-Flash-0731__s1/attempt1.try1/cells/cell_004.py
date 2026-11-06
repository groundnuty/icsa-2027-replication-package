
import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values

# Region: lat 58.69 to 59.89, lon 18.69 to 19.89, inclusive
lat_mask = (lat >= 58.69) & (lat <= 59.89)
lon_mask = (lon >= 18.69) & (lon <= 19.89)

lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

print("lat range:", lat[lat_idx[0]], "to", lat[lat_idx[-1]])
print("lon range:", lon[lon_idx[0]], "to", lon[lon_idx[-1]])
print("Number of lat cells:", len(lat_idx))
print("Number of lon cells:", len(lon_idx))
print("Lat indices:", lat_idx[0], "to", lat_idx[-1])
print("Lon indices:", lon_idx[0], "to", lon_idx[-1])
