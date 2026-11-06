import xarray as xr
import numpy as np

# Try without chunks
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("\nTime range:", ds.time.values[0], "to", ds.time.values[-1])
print("Lat range:", ds.latitude.values[0], "to", ds.latitude.values[-1])
print("Lon range:", ds.longitude.values[0], "to", ds.longitude.values[-1])
print("Time count:", len(ds.time))
print("Lat count:", len(ds.latitude))
print("Lon count:", len(ds.longitude))
