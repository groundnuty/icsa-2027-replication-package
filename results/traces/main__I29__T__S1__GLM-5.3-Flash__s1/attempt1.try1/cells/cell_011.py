import xarray as xr, fsspec, numpy as np, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
t0=time.time()
n=0
for i in range(5):
    f = fs.open(base+'sst_1992060%d.nc'%(1+i),'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    reg = ds['analysed_sst'].isel(time=0).isel(latitude=slice(218,278), longitude=slice(601,661)).values
    ds.close(); f.close()
    n+=np.isnan(reg).sum()
t1=time.time()
print('5 files xarray', t1-t0, n)
