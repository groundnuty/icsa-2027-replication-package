
import xarray as xr, numpy as np, pandas as pd
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
sub=ds.sel(latitude=slice(58.69,59.89),longitude=slice(18.69,19.89))
print(sub.latitude.values, sub.longitude.values)
full=pd.date_range('1991-12-27','2003-01-05')
tb=sub.time.sel(time=slice('1991-12-27','2003-01-05')).to_index()
print(len(tb), len(full), tb.equals(full))
tt=sub.time.sel(time=slice('2010-06-01','2010-08-31')).to_index(); print(len(tt))
