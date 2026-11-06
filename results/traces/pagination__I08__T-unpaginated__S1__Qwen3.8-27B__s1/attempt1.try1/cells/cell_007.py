
import os, sys
os.makedirs('output', exist_ok=True)
os.makedirs('work', exist_ok=True)
with open('work/marker.txt', 'w') as f:
    f.write('hello persistence')
print("cwd:", os.getcwd())
print("numpy:", __import__('numpy').__version__)
import xarray, h5netcdf
print("xarray:", xarray.__version__, "h5netcdf:", h5netcdf.__version__)
