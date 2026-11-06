import numpy as np, time, sys, os
print('numpy', np.__version__, 'python', sys.version)
try:
    import scipy; print('scipy', scipy.__version__)
except Exception as e: print('no scipy', e)
try:
    import netCDF4; print('netCDF4', netCDF4.__version__)
except Exception as e: print('no netCDF4', e)
import xarray as xr
print('xr', xr.__version__, 'engines', list(xr.backends.list_engines()))
# persistence test
with open('persist_test.txt','w') as fh: fh.write('hello')
print('cwd', os.getcwd())
