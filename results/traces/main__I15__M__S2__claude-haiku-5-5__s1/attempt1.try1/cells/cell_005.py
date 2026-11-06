
import xarray as xr, numpy as np, pandas as pd, json, os
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ila=np.where((lat>=56.13)&(lat<=57.33))[0]; ilo=np.where((lon>=17.71)&(lon<=18.91))[0]
sub=ds.analysed_sst.isel(latitude=ila,longitude=ilo)
b=sub.sel(time=slice('1991-12-27','2003-01-05'))
base=b.values.astype(np.float64); btime=pd.DatetimeIndex(b.time.values)
tg=sub.sel(time=slice('2019-06-01','2019-08-31'))
tv=tg.values.astype(np.float64); ttime=pd.DatetimeIndex(tg.time.values)
os.makedirs('/tmp/w',exist_ok=True)
np.savez('/tmp/w/d.npz',base=base,btime=btime.values.astype('datetime64[ns]').astype('int64'),tv=tv,ttime=ttime.values.astype('datetime64[ns]').astype('int64'),lat=lat[ila],lon=lon[ilo])
print(base.shape, tv.shape, np.isnan(base).mean(), np.isnan(tv).mean(), btime[0], btime[-1], ttime[0], ttime[-1])
print(np.nanmin(tv), np.nanmax(tv))
