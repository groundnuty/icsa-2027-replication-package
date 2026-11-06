import os, sys
print(sys.version)
import numpy as np
print("numpy", np.__version__)
for mod in ("xarray", "h5netcdf", "netCDF4", "h5py", "pandas"):
    try:
        m = __import__(mod)
        print(mod, getattr(m, "__version__", "?"))
    except Exception as e:
        print(mod, "ERR", e)
base = "/data/icsa2027_data_20261101T090944Z/s1z"
print("isdir:", os.path.isdir(base))
names = sorted(os.listdir(base))
print("n entries:", len(names))
for n in names[:40]:
    try:
        print(n, os.path.getsize(os.path.join(base, n)))
    except Exception as e:
        print(n, "ERR", e)
