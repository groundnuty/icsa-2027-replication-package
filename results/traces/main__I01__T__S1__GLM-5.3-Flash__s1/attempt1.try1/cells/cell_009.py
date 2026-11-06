import numpy as np, sys
print('python', sys.version)
print('numpy', np.__version__)
try:
    import scipy; print('scipy', scipy.__version__)
except Exception as e: print('no scipy:', e)
try:
    import netCDF4; print('netCDF4', netCDF4.__version__)
except Exception as e: print('no netCDF4:', e)
try:
    import h5netcdf; print('h5netcdf', h5netcdf.__version__)
except Exception as e: print('no h5netcdf:', e)
# check hazen availability
try:
    q = np.quantile(np.arange(1.,11.), 0.9, method='hazen')
    print('hazen q90 of 1..10:', q)  # expect 9.5
except Exception as e:
    print('hazen not available:', e)
import pandas as pd
print('pandas', pd.__version__)
