
import fsspec, xarray as xr, numpy as np, pandas as pd, os, json
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v=ds.analysed_sst
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.41-1e-6)&(lat<=58.61+1e-6))[0]; lo=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
sub = v.isel(latitude=la, longitude=lo)
base = sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tgt = sub.sel(time=slice('2013-06-01','2013-08-31')).load()
os.makedirs('output', exist_ok=True)
bt = pd.DatetimeIndex(base.time.values)
bvals = base.values.astype(np.float64)
def doy(ts):
    return np.array([pd.Timestamp(2000, t.month, t.day).dayofyear for t in ts])
bdoy = doy(bt)
anchor = bt[(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))]
adoy = doy(anchor)
thr = np.full((367,)+bvals.shape[1:], np.nan)
clim = np.full((367,)+bvals.shape[1:], np.nan)
for d in range(1,367):
    if d==60: continue
    anc = anchor[adoy==d]
    if len(anc)==0: continue
    mask = np.zeros(len(bt),bool)
    for b in anc:
        mask |= np.abs((bt-b).days)<=5
    pool = bvals[mask]
    thr[d] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim[d] = np.nanmean(pool, axis=0)
print("days filled:", np.sum(~np.isnan(thr[1:,0,0])), "missing:", [d for d in range(1,367) if np.isnan(thr[d,0,0])])
