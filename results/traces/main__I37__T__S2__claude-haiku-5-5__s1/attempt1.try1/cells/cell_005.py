
import fsspec, xarray as xr, numpy as np, pandas as pd
fs = fsspec.filesystem('onedata')
f=fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds=xr.open_dataset(f,engine='h5netcdf')
sub=ds.sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2012-06-01','2012-08-31')).load()
print(b.shape,t.shape, np.isnan(b.values).sum(), np.isnan(t.values).sum())
print(b.time.values[0], b.time.values[-1], t.time.values[0], t.time.values[-1])
