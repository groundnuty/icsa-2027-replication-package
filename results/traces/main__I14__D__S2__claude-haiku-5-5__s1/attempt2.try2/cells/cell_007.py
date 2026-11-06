
import subprocess
base = r'''
import numpy as np, xarray as xr, time, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
la=ds.latitude.values; lo=ds.longitude.values
m_la=(la>=56.13-1e-6)&(la<=57.33+1e-6); m_lo=(lo>=17.71-1e-6)&(lo<=18.91+1e-6)
li=np.where(m_la)[0]; oi=np.where(m_lo)[0]
sub = ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1), longitude=slice(oi[0],oi[-1]+1))
tb = sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tt = sub.sel(time=slice('2015-06-01','2015-08-31')).load()
A=tb.values.astype(np.float64); T=tt.values.astype(np.float64)
sea = np.all(np.isfinite(T),axis=0)
bdates = pd.DatetimeIndex(tb.time.values)
doy_of = lambda ts: np.array([pd.Timestamp(2000, t.month, t.day).dayofyear for t in ts])
pool_idx = {d: [] for d in range(1,367) if d!=60}
for y in range(1992,2003):
    for b in pd.date_range(f'{y}-01-01', f'{y}-12-31'):
        d = pd.Timestamp(2000, b.month, b.day).dayofyear
        if d==60: continue
        ib = bdates.get_loc(b)
        for k in range(-5,6):
            pool_idx[d].append(ib+k)
thr = np.full((366,)+A.shape[1:], np.nan); clim = np.full_like(thr, np.nan)
for d in pool_idx:
    idx = np.array(pool_idx[d]); assert len(np.unique(idx))==len(idx)
    P = A[idx]
    thr[d-1] = np.nanquantile(P, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(P, axis=0)
thr[59] = (thr[58]+thr[60])/2; clim[59] = (clim[58]+clim[60])/2
def smooth(x):
    out = np.empty_like(x)
    for d in range(366):
        ids = [(d+k)%366 for k in range(-15,16)]
        out[d] = x[ids].mean(axis=0)
    return out
thr_s = smooth(thr)
tdates = pd.DatetimeIndex(tt.time.values)
tdoy = doy_of(tdates)
hot = (T >= thr_s[tdoy-1]) & sea[None]
nt = T.shape[0]
def runs(b):
    out=[]; i=0
    while i<len(b):
        if b[i]:
            j=i
            while j+1<len(b) and b[j+1]: j+=1
            out.append([i,j]); i=j+1
        else: i+=1
    return out
def merge(segs, h, strict):
    if not segs: return []
    m=[list(segs[0])]
    for s in segs[1:]:
        gap = s[0]-m[-1][1]-1
        gapdays = h[m[-1][1]+1:s[0]]
        ok = 1<=gap<=2 and (not strict or not gapdays.any())
        if ok: m[-1][1]=s[1]
        else: m.append(list(s))
    return m
mhw = np.zeros(hot.shape, bool); mhw_var = np.zeros(hot.shape, bool)
for a in range(hot.shape[1]):
    for b_ in range(hot.shape[2]):
        if not sea[a,b_]: continue
        h = hot[:,a,b_]
        segs = [s for s in runs(h) if s[1]-s[0]+1>=5]
        for s in merge(segs, h, True): mhw[s[0]:s[1]+1, a, b_]=True
        for s in merge(segs, h, False): mhw_var[s[0]:s[1]+1, a, b_]=True
ndiff = int((mhw!=mhw_var).sum())
print('variant differs cell-days:', ndiff)
active = mhw.any(axis=(1,2))
events=[]; i=0
while i<nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        events.append((str(tdates[i].date()), str(tdates[j].date()))); i=j+1
    else: i+=1
print('events', events)
print('active days', int(active.sum()), 'mhw cell-days', int(mhw.sum()), 'nt', nt, 'sea', int(sea.sum()), 'thr finite cells', int(np.isfinite(thr_s[0]).sum()))
os.makedirs('/work/output', exist_ok=True)
out = xr.Dataset({'mhw': (('time','lat','lon'), mhw.astype(np.uint8))},
    coords={'time': tt.time.values, 'lat': tt.latitude.values, 'lon': tt.longitude.values})
out['mhw'].attrs={'long_name':'marine heatwave flag'}
out.to_netcdf('/work/output/mhw_mask.nc')
rep = {"region":{"lat_min":56.13,"lat_max":57.33,"lon_min":17.71,"lon_max":18.91},
       "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
       "target_analysed":{"start":"2015-06-01","end":"2015-08-31"},
       "events":[{"onset":a_,"end":b2} for a_,b2 in events],
       "complete": True,
       "caveats": "Land cells set to 0. Gap-joining requires gap days all non-hot; the variant without this condition differs on %d cell-days. Sea cells = finite on all target days (3300 of 3600). Baseline pool includes the specified window edges 1991-12-27..2003-01-05." % ndiff}
json.dump(rep, open('/work/output/report.json','w'), indent=2)
print(json.dumps(rep)[:1500])
'''
open('/work/b.py','w').write(base)
r=subprocess.run(['python','/work/b.py'],capture_output=True,text=True); print(r.stdout[-5000:], r.stderr[-3000:])
