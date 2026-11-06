import sys, os, multiprocessing, time
import numpy as np
print("python:", sys.version)
print("numpy:", np.__version__)
print("nproc:", multiprocessing.cpu_count())
try:
    import h5py; print("h5py:", h5py.__version__)
except Exception as e: print("h5py err", e)
try:
    import h5netcdf; print("h5netcdf:", h5netcdf.__version__)
except Exception as e: print("h5netcdf err", e)
try:
    import netCDF4; print("netCDF4:", netCDF4.__version__)
except Exception as e: print("netCDF4 err", e)
try:
    import scipy; print("scipy:", scipy.__version__)
except Exception as e: print("scipy err", e)
