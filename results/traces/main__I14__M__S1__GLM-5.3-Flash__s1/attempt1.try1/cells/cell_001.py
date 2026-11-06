import os, sys, platform
print("python:", sys.version)
import numpy as np, xarray as xr
print("numpy:", np.__version__, "xarray:", xr.__version__)
try:
    import h5netcdf; print("h5netcdf:", h5netcdf.__version__)
except Exception as e: print("h5netcdf missing:", e)
try:
    import netCDF4; print("netCDF4:", netCDF4.__version__)
except Exception as e: print("netCDF4 missing:", e)

d = "/data/icsa2027_data_20261101T090944Z/s1z"
print("cwd:", os.getcwd())
entries = sorted(os.listdir(d))
print("n entries:", len(entries))
for f in entries[:15]: print(" ", f)
print(" ...")
for f in entries[-8:]: print(" ", f)
