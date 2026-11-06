import fsspec, xarray as xr, numpy as np, datetime as dt, os
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
def load(date):
    s=date.strftime('%Y%m%d')
    with fs.open(P+f'sst_{s}.nc','rb') as f:
        x=xr.open_dataset(f,engine='h5netcdf').load()
    return x
with fs.open(P+'sst_20100601.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf').load()
print(d.analysed_sst.attrs)
lat=d.latitude.values; lon=d.longitude.values
print(np.diff(lat[:3]), np.diff(lon[:3]))
ilat=np.where((lat>=57.13-1e-4)&(lat<=58.33+1e-4))[0]; ilon=np.where((lon>=22.79-1e-4)&(lon<=23.99+1e-4))[0]
print(len(ilat),len(ilon), lat[ilat[[0,-1]]], lon[ilon[[0,-1]]])
print(d.analysed_sst.values[0][np.ix_(ilat,ilon)].dtype)