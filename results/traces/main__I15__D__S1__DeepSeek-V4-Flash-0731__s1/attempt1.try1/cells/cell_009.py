
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("Time range:", ds.time.values[0], ds.time.values[-1])
print("Lat range:", ds.latitude.values[0], ds.latitude.values[-1])
print("Lon range:", ds.longitude.values[0], ds.longitude.values[-1])
print("Lat step:", ds.latitude.values[1]-ds.latitude.values[0])
print("Lon step:", ds.longitude.values[1]-ds.longitude.values[0])
print("Shape:", ds.analysed_sst.shape)
