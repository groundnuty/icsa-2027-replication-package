
import fsspec, xarray as xr, numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
fs = fsspec.filesystem('onedata')
f=fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds=xr.open_dataset(f,engine='h5netcdf')
v=ds.analysed_sst
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=57.33)&(lat<=58.53))[0]; lo=np.where((lon>=9.03)&(lon<=10.23))[0]
times=pd.DatetimeIndex(ds.time.values)
# check daily contiguity
print(times.to_series().diff().dropna().value_counts())
ext_start=pd.Timestamp('1991-12-27'); ext_end=pd.Timestamp('2003-01-05')
tgt_start=pd.Timestamp('2012-06-01'); tgt_end=pd.Timestamp('2012-08-31')
need=times[((times>=ext_start)&(times<=ext_end))|((times>=tgt_start)&(times<=tgt_end))]
idx=np.where(times.isin(need))[0]
sub=v.isel(time=idx,latitude=li,longitude=lo).values.astype(np.float64)
T=times[idx]
print(sub.shape, T[0], T[-1], np.isnan(sub).mean())
os.makedirs('/tmp/w',exist_ok=True)
np.save('/tmp/w/sub.npy',sub); T.to_series().to_csv('/tmp/w/T.csv')
np.save('/tmp/w/lat.npy',lat[li]); np.save('/tmp/w/lon.npy',lon[lo])
