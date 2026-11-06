import sys
print(sys.version)
import numpy as np
print("numpy", np.__version__)
try:
    import xarray as xr
    print("xarray", xr.__version__)
except Exception as e:
    print("xarray import fail:", e)
try:
    import h5netcdf
    print("h5netcdf", h5netcdf.__version__)
except Exception as e:
    print("h5netcdf import fail:", e)
import os
print("file size:", os.path.getsize("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"))
