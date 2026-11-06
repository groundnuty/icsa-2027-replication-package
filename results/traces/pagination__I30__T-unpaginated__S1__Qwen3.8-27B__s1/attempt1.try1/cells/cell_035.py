
import os, json
print('cwd:', os.getcwd())
print('existing output dir:', os.listdir('.') if os.path.isdir('output') else 'no output dir')
import xarray as xr
print('xarray', xr.__version__)
try:
    import netCDF4; print('netCDF4', netCDF4.__version__)
except Exception as e:
    print('netCDF4 unavailable:', e)
try:
    import h5netcdf; print('h5netcdf', h5netcdf.__version__)
except Exception as e:
    print('h5netcdf unavailable:', e)
