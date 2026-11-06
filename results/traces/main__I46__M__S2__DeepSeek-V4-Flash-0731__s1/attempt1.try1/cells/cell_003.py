
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds.latitude.values
lon = ds.longitude.values
time = ds.time.values

print("lat range:", lat.min(), lat.max())
print("lon range:", lon.min(), lon.max())
print("time range:", time.min(), time.max())
print("n time:", len(time))
print("lat step:", np.diff(lat)[:5])
print("lon step:", np.diff(lon)[:5])
