import shutil, os
total, used, free = shutil.disk_usage('/work')
print(f'/work total={total/1e9:.1f}GB used={used/1e9:.1f}GB free={free/1e9:.1f}GB')
print(os.getcwd())
os.makedirs('/work/output', exist_ok=True)
import numpy, xarray, h5netcdf
print('numpy', numpy.__version__, 'xarray', xarray.__version__, 'h5netcdf', h5netcdf.__version__)
