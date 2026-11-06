script = r'''
import pandas as pd, numpy as np, xarray as xr, json, os, warnings
warnings.filterwarnings('ignore')
sub = xr.open_dataset('/work/sub.nc', engine='h5netcdf')
A = sub.analysed_sst.values.astype(np.float64)  # (4120,60,60)
T = pd.DatetimeIndex(np.load('/work/subtime.npy'))
lat = sub.latitude.values; lon = sub.longitude.values
tgt = ((T>=pd.Timestamp('2008-06-01'))&(T<=pd.Timestamp('2008-08-31')))
fin_t = np.isfinite(A[tgt]).all(axis=0)
def doy(ts): return pd.Timestamp(2000, ts.month, ts.day).day_of_year
pos = {d:i for i,d in enumerate(T)}
anchors = pd.date_range('1992-01-01','2002-12-31')
pools = {d: [] for d in range(1,367) if d!=60}
for b in anchors:
    d = doy(b)
    if d==60: continue
    for k in range(-5,6):
        pools[d].append(pos[b+pd.Timedelta(days=k)])
for d in pools: assert len(set(pools[d]))==len(pools[d])
shape=A.shape[1:]
thr = np.full((366,)+shape, np.nan); clim = np.full((366,)+shape, np.nan)
for d in range(1,367):
    if d==60: continue
    P = A[pools[d]]
    thr[d-1] = np.nanquantile(P, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(P, axis=0)
thr[59] = (thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(x):
    out = np.zeros_like(x)
    for k in range(-15,16):
        out += np.roll(x, -k, axis=0)
    return out/31
thr_s = smooth(thr); clim_s = smooth(clim)
print('nan thr sea', np.isnan(thr_s[:,fin_t]).sum(), 'nan clim sea', np.isnan(clim_s[:,fin_t]).sum())
ii=(30,30)
print('thr sample', thr_s[[0,59,181,365],30,30].round(3), 'clim', clim_s[[0,59,181,365],30,30].round(3))

Tt = T[tgt]; At = A[tgt]
dt = np.array([doy(x) for x in Tt])
thr_t = thr_s[dt-1]   # (92,60,60)
hot = At >= thr_t
hot = hot & fin_t[None]  # non-sea cells never in MHW
mhw = np.zeros(hot.shape, dtype=bool)
def runs(x):
    # return list of (start,end) inclusive of True runs
    r=[]; n=len(x); i=0
    while i<n:
        if x[i]:
            j=i
            while j+1<n and x[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
nt = hot.shape[0]
for ci in range(shape[0]):
    for cj in range(shape[1]):
        if not fin_t[ci,cj]: continue
        rs = [r for r in runs(hot[:,ci,cj]) if r[1]-r[0]+1>=5]
        if not rs: continue
        # join MHWs separated by 1 or 2 non-hot days
        ev=[list(rs[0])]
        for s,e in rs[1:]:
            gap = s-ev[-1][1]-1
            if gap<=2: ev[-1][1]=e
            else: ev.append([s,e])
        for s,e in ev: mhw[s:e+1,ci,cj]=True
active = mhw.any(axis=(1,2))
ev_reg = runs(active)
events=[{"onset": str(Tt[s].date()), "end": str(Tt[e].date())} for s,e in ev_reg]
print('n sea cells', fin_t.sum(), 'mhw cell-days', mhw.sum(), 'active days', active.sum())
print('events', events)
os.makedirs('/work/../output', exist_ok=True) if False else None
os.makedirs('output', exist_ok=True)
import xarray as xr
out = xr.Dataset({'mhw': (('time','lat','lon'), mhw.astype(np.uint8))},
    coords={'time': Tt.values, 'lat': lat, 'lon': lon})
out.mhw.encoding={}
out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
report = {
 "region": {"lat_min":57.83,"lat_max":59.03,"lon_min":17.41,"lon_max":18.61},
 "baseline_analysed": {"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed": {"start":"2008-06-01","end":"2008-08-31"},
 "events": events,
 "complete": True,
 "caveats": "Region grid cells used: lat 57.84-59.02, lon 17.42-18.60 (60x60 on 0.02 deg grid). Sea cells = 3294 finite on all target days; land cells are 0. Source: single file sst_s2.nc (1982-2023) subset; daily 1982-1984 files were not used. Threshold/climatology use pool windows from 1991-12-27 to 2003-01-05. Joining of MHWs applied only to runs >=5 days with gaps of 1-2 non-hot days."
}
json.dump(report, open('output/report.json','w'), indent=2)
print('written')
'''
open('/work/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/run.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout[-6000:], r.stderr[-3000:])