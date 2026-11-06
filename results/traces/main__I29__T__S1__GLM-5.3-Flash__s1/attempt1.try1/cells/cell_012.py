import xarray as xr, fsspec, numpy as np, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
t0=time.time()
for i in range(20):
    y,m,d = 1992,6,1+i
    f = fs.open(base+'sst_%04d%02d%02d.nc'%(y,m,d),'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    reg = ds['analysed_sst'].isel(time=0, latitude=slice(218,278), longitude=slice(601,661)).values.astype(np.float64)
    ds.close(); f.close()
t1=time.time()
print('20 files xarray', t1-t0)
t0=time.time()
for i in range(20):
    y,m,d = 1992,6,1+i
    f = fs.open(base+'sst_%04d%02d%02d.nc'%(y,m,d),'rb')
    ds = xr.open_dataset(f, engine='h5netcdf', chunks={})
    reg = ds['analysed_sst'].isel(time=0, latitude=slice(218,278), longitude=slice(601,661)).values
    ds.close(); f.close()
t1=time.time()
print('20 files dask', t1-t0)
