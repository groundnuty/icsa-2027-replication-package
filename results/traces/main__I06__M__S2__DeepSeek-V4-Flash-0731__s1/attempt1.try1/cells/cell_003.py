
import xarray as xr
import numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds.latitude.values
lon = ds.longitude.values
time = ds.time.values
print("lat range:", lat.min(), lat.max(), "n=", len(lat))
print("lon range:", lon.min(), lon.max(), "n=", len(lon))
print("time range:", time.min(), time.max(), "n=", len(time))

# region
lat_sel = (lat >= 54.45) & (lat <= 55.65)
lon_sel = (lon >= 16.05) & (lon <= 17.25)
print("lat indices:", np.where(lat_sel)[0])
print("lon indices:", np.where(lon_sel)[0])
