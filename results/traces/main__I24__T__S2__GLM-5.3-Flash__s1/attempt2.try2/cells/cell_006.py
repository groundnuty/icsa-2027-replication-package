import sys
print(sys.version)
import numpy as np
print("numpy", np.__version__)
for m in ("scipy","dask","netCDF4","h5py","h5netcdf","fsspec","pandas","xarray"):
    try:
        mod = __import__(m)
        print(m, getattr(mod, "__version__", "?"))
    except Exception as e:
        print(m, "MISSING", e)
