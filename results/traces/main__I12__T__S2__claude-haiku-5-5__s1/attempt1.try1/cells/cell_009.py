
import fsspec, xarray as xr, numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=56.09)&(lat<=57.29))[0]; lo=np.where((lon>=10.55)&(lon<=11.75))[0]
sub = ds.analysed_sst.isel(latitude=slice(la[0],la[-1]+1), longitude=slice(lo[0],lo[-1]+1))
sub = sub.sel(time=slice('1991-12-27','2009-08-31')).load()
t = pd.DatetimeIndex(sub.time.values)
V = sub.values.astype(np.float64); T=len(t)
doy = np.array([x.replace(year=2000).dayofyear for x in t])
base_idx = np.where((t>=pd.Timestamp('1992-01-01'))&(t<=pd.Timestamp('2002-12-31')))[0]
pools = {d: set() for d in range(1,367) if d!=60}
for b in base_idx:
    d = doy[b]
    if d==60: continue
    pools[d].update(range(max(b-5,0), min(b+5,T-1)+1))
thr = np.full((367,60,60), np.nan); clim = np.full((367,60,60), np.nan)
for d in range(1,367):
    if d==60: continue
    P = V[np.array(sorted(pools[d]))]
    thr[d] = np.nanpercentile(P, 90, axis=0, method='hazen')
    clim[d] = np.nanmean(P, axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    arr=a[1:]
    ext=np.concatenate([arr[-15:],arr,arr[:15]],axis=0)
    out=np.full_like(a,np.nan); out[1:]=np.stack([ext[i:i+31].mean(axis=0) for i in range(366)]); return out
thr_s=smooth(thr); clim_s=smooth(clim)
tgt=np.where((t>=pd.Timestamp('2009-06-01'))&(t<=pd.Timestamp('2009-08-31')))[0]
Vt=V[tgt]; tdoy=doy[tgt]; tdates=t[tgt]
sea=np.all(np.isfinite(Vt),axis=0)
hot=(Vt>=thr_s[tdoy])&sea[None]&np.isfinite(thr_s[tdoy])
mhw=np.zeros_like(hot)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h=hot[:,i,j]; runs=[]; k=0; n=len(h)
        while k<n:
            if h[k]:
                s=k
                while k<n and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0; n=len(active)
while k<n:
    if active[k]:
        s=k
        while k<n and active[k]: k+=1
        events.append({"onset":str(tdates[s].date()),"end":str(tdates[k-1].date())})
    else: k+=1
os.makedirs('output',exist_ok=True)
out = xr.Dataset({"mhw": (("time","lat","lon"), mhw.astype(np.uint8))},
    coords={"time": tdates.values, "lat": sub.latitude.values, "lon": sub.longitude.values})
out.to_netcdf('output/mhw_mask.nc')
report = {
 "region": {"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},
 "baseline_analysed": {"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed": {"start":"2009-06-01","end":"2009-08-31"},
 "events": events,
 "complete": True,
 "caveats": "Region grid is 60x60 cells (lat 56.10-57.28, lon 10.56-11.74); 3296 sea cells finite on all target days, others set to 0. Threshold: hazen 90th percentile over +/-5-day windows, day 60 averaged, 31-day wrap smoothing. Gap joining applied to per-cell MHWs (gap days included). Region reported as requested bounds."
}
json.dump(report, open('output/report.json','w'), indent=1)
print(json.dumps(report)); print(xr.open_dataset('output/mhw_mask.nc').mhw.shape, int(mhw.sum()), int(sea.sum()))
