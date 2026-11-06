import os
print(os.listdir('/'))
print(os.listdir('/work') if os.path.exists('/work') else "no /work")
import xarray, numpy, netCDF4, h5netcdf
print(xarray.__version__, numpy.__version__, h5netcdf.__version__)
import shutil
print(shutil.disk_usage('/work').free / 1e9, "GB free in /work")
