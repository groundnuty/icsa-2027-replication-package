import time, xarray as xr, numpy as np
t=time.time()
fs.get(base+'sst_20120601.nc','/work/s/t.nc')
print(time.time()-t, os.path.getsize('/work/s/t.nc'))
ds=xr.open_dataset('/work/s/t.nc',engine='h5netcdf')
print(ds.analysed_sst.attrs, ds.analysed_sst.encoding)
print(ds.time.values, ds.latitude.size, ds.longitude.size)