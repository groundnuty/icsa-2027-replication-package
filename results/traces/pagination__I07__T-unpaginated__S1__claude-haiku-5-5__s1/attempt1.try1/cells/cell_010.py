
script = r'''
import numpy as np, pandas as pd, datetime as _dt, json, os
import xarray as xr
Z=np.load('/tmp/w/sub.npz', allow_pickle=True)
sst=Z['sst']; dates=pd.to_datetime(Z['dates']); LAT=Z['lat']; LON=Z['lon']
t0=dates[0]
def idx(d): return int((pd.Timestamp(d)-t0).days)
doy_of=lambda ts: _dt.date(2000, ts.month, ts.day).timetuple().tm_yday
doys=np.array([doy_of(x) for x in dates])
base_mask=(dates>=pd.Timestamp('1992-01-01'))&(dates<=pd.Timestamp('2002-12-31'))
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
sst64=sst.astype(np.float64)
for d in range(1,367):
    if d==60: continue
    bdates=dates[base_mask & (doys==d)]
    idxs=set()
    for b in bdates:
        for k in range(-5,6):
            idxs.add(idx(b+pd.Timedelta(days=k)))
    idxs=sorted(idxs)
    pool=sst64[idxs]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    with np.errstate(all='ignore'):
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    b=a[1:367]
    out=np.empty_like(b)
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i]=b[ii].mean(axis=0)
    return out
thr_s=smooth(thr)
tm=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
sea=np.isfinite(sst64[tm]).all(axis=0)
tdates=dates[tm]; tsst=sst64[tm]; tdoy=doys[tm]
T=thr_s[tdoy-1]
hot=(tsst>=T)
hot&=sea[None]
nt=len(tdates)
mhw=np.zeros((nt,60,60),bool)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        runs=[]; s=None
        for t in range(nt+1):
            v=bool(h[t]) if t<nt else False
            if v and s is None: s=t
            if not v and s is not None:
                if t-s>=5: runs.append([s,t-1])
                s=None
        if not runs: continue
        merged=[runs[0]]
        for r in runs[1:]:
            gap=r[0]-merged[-1][1]-1
            if gap<=2: merged[-1]=[merged[-1][0], r[1]]
            else: merged.append(r)
        for a,b in merged: mhw[a:b+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; s=None
for t in range(nt+1):
    v=bool(active[t]) if t<nt else False
    if v and s is None: s=t
    if not v and s is not None:
        events.append({"onset":str(tdates[s].date()),"end":str(tdates[t-1].date())}); s=None
print('nt',nt,'sea',sea.sum(),'days active', active.sum(), 'cell-days', mhw.sum())
print('nan thr sea cells', np.isnan(thr_s[:, sea]).sum())
print(events)
print('hot cells per day max', hot.sum(axis=(1,2)).max())
os.makedirs('/tmp/w/out',exist_ok=True)
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'), mhw.astype(np.uint8))},
    coords={'time':tdates.values,'lat':LAT,'lon':LON})
ds['mhw'].attrs={'long_name':'marine heatwave flag'}
ds.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8','zlib':True}})
report={"region":{"lat_min":54.45,"lat_max":55.65,"lon_min":16.05,"lon_max":17.25},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
 "events":events,"complete":True,
 "caveats":"Baseline pools use 1991-12-27..2003-01-05 windows as specified. Per-cell MHWs filtered to >=5 days before gap-joining (1-2 day gaps). Land cells (non-finite on target days) are 0. Regional events truncated at target period boundaries."}
json.dump(report, open('output/report.json','w'), indent=2)
print('written')
'''
open('/tmp/w/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/w/run.py'],capture_output=True,text=True,cwd='/tmp/w')
print(r.stdout[-5000:], r.stderr[-3000:])
