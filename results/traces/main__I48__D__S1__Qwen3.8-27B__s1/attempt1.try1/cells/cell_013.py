import numpy as np, xarray as xr
ds = xr.open_dataset('/work/data/sst_19911227.nc', engine='h5netcdf')
v = ds['analysed_sst']
try:
    print(v['time'])
except Exception as e:
    print("ERR1:", type(e).__name__, e)
print("coord time:", ds['time'].values)
ds.close()
