import xarray as xr,pandas as pd,numpy as np
fs=sorted(os.listdir(d));print(fs[0],fs[-1])
ds=xr.open_dataset(d+'/sst_20090601.nc',engine='h5netcdf');print(ds)
have={f[4:12] for f in fs}
need=pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d')
print([n for n in need if n not in have][:20])
need=pd.date_range('2009-06-01','2009-08-31').strftime('%Y%m%d');print([n for n in need if n not in have])