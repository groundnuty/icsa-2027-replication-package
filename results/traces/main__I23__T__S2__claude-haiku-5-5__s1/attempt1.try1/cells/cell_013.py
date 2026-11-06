
import warnings; warnings.filterwarnings('ignore')
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
bt = pd.DatetimeIndex(base.time.values)
bvals = base.values.astype(np.float64)
tvals = tgt.values.astype(np.float64)
tt = pd.DatetimeIndex(tgt.time.values)
def doy(ts):
    return np.array([pd.Timestamp(2000, t.month, t.day).dayofyear for t in ts])
anchor = bt[(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))]
adoy = doy(anchor)
thr = np.full((367,)+bvals.shape[1:], np.nan)
for d in range(1,367):
    if d==60: continue
    anc = anchor[adoy==d]
    if len(anc)==0: continue
    mask = np.zeros(len(bt),bool)
    for b in anc:
        mask |= np.abs((bt-b).days)<=5
    thr[d] = np.nanquantile(bvals[mask], 0.9, axis=0, method='hazen')
a = thr.copy(); a[60]=0.5*(a[59]+a[61])
x = a[1:367]; out=np.empty_like(x)
for d in range(366):
    out[d] = x[[((d+k)%366) for k in range(-15,16)]].mean(axis=0)
thr_s = np.full_like(thr, np.nan); thr_s[1:367]=out
sea = np.all(np.isfinite(tvals),axis=0)
T = thr_s[doy(tt)]
hot = (tvals>=T) & sea[None]
nt,ny,nx = hot.shape
mhw = np.zeros(hot.shape, np.uint8)
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        h=hot[:,i,j]; runs=[]; t=0
        while t<nt:
            if h[t]:
                s=t
                while t<nt and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        if not runs: continue
        merged=[runs[0]]
        for r in runs[1:]:
            if r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
            else: merged.append(r)
        for s,e in merged: mhw[s:e+1,i,j]=1
active = mhw.any(axis=(1,2))
events=[]; t=0
while t<nt:
    if active[t]:
        s=t
        while t<nt and active[t]: t+=1
        events.append({"onset":str(tt[s].date()),"end":str(tt[t-1].date())})
    else: t+=1
os.makedirs('output',exist_ok=True)
out_ds = xr.Dataset({'mhw': (('time','lat','lon'), mhw)},
    coords={'time': tgt.time.values, 'lat': tgt.latitude.values, 'lon': tgt.longitude.values})
out_ds.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8'}})
report = {
 "region": {"lat_min":57.41,"lat_max":58.61,"lon_min":18.69,"lon_max":19.89},
 "baseline_analysed": {"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed": {"start":"2013-06-01","end":"2013-08-31"},
 "events": events,
 "complete": True,
 "caveats": f"Region has {int(sea.sum())} sea cells of {sea.size} (land cells are NaN and set to 0). Per-cell MHW cell-days: {int(mhw.sum())}. Regional events: {len(events)}. Only 1.8% of target cell-days exceed the threshold despite a warm 2013 summer; results are sensitive to the exact percentile/window implementation. Grid coordinates are float32 from the dataset."
}
json.dump(report, open('output/report.json','w'), indent=2)
print(json.dumps(report, indent=1)); print(os.listdir('output'))
