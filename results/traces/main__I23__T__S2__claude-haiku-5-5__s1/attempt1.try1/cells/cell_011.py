
import warnings; warnings.filterwarnings('ignore')
import fsspec, xarray as xr, numpy as np, pandas as pd
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v=ds.analysed_sst
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.41-1e-6)&(lat<=58.61+1e-6))[0]; lo=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
sub = v.isel(latitude=la, longitude=lo)
base = sub.sel(time=slice('1992-01-01','2002-12-31')).load()
tgt = sub.sel(time=slice('2013-06-01','2013-08-31')).load()
bt=pd.DatetimeIndex(base.time.values); tt=pd.DatetimeIndex(tgt.time.values)
bv=base.values.astype(float); tv=tgt.values.astype(float)
sea=np.all(np.isfinite(tv),0)
# summer baseline values (Jun-Aug) mean, and 2013 summer mean
bm=(bt.month>=6)&(bt.month<=8)
print("baseline JJA mean (sea):", np.nanmean(bv[bm][:,sea]), " 2013 JJA mean:", np.nanmean(tv[:,sea]))
print("baseline JJA 90th pct of pooled values:", np.nanquantile(bv[bm][:,sea],0.9))
print("2013 JJA frac >= that:", np.mean(tv[:,sea]>=np.nanquantile(bv[bm][:,sea],0.9)))
print("baseline JJA frac>= 90th pct overall:", np.mean(bv[bm][:,sea]>=np.nanquantile(bv[bm][:,sea],0.9)))
