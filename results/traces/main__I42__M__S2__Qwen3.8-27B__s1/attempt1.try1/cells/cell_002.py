import xarray as xr
import numpy as np

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
print(ds)
print("---- attrs time ----")
print("time units:", ds.time.encoding if 'time' in ds else None)
print("time attrs:", dict(ds.time.attrs) if 'time' in ds else None)
print("lat range:", float(ds.lat.min()), float(ds.lat.max()), "len:", len(ds.lat))
print("lon range:", float(ds.lon.min()), float(ds.lon.max()), "len:", len(ds.lon))
