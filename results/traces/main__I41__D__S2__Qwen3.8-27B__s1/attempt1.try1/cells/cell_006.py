import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
sst = ds['analysed_sst']
print(sst.attrs)
print(sst.encoding)
print("time encoding:", ds['time'].encoding)
print(ds['time'].values[:3], ds['time'].values[-3:])
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat dtype", lat.dtype, "lon dtype", lon.dtype)
# check grid alignment with boundaries
print("lat values near 61.57:", lat[(lat>61.5)&(lat<61.65)])
print("lat values near 62.77:", lat[(lat>62.7)&(lat<62.85)])
print("lon values near 20.17:", lon[(lon>20.1)&(lon<20.25)])
print("lon values near 21.37:", lon[(lon>21.3)&(lon<21.45)])
ds.close()
