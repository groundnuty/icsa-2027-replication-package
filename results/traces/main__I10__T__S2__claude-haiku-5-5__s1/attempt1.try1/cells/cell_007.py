
script = r'''
import fsspec, xarray as xr, numpy as np, pandas as pd, datetime as dt, json, os, warnings
warnings.filterwarnings('ignore')
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v = ds.analysed_sst
lat_all = ds.latitude.values.astype(np.float64); lon_all = ds.longitude.values.astype(np.float64)
LAT0,LAT1,LON0,LON1 = 55.67,56.87,16.45,17.65
li = np.where((lat_all>=LAT0)&(lat_all<=LAT1))[0]
lo = np.where((lon_all>=LON0)&(lon_all<=LON1))[0]
assert np.all(np.diff(li)==1) and np.all(np.diff(lo)==1)
latv = lat_all[li]; lonv = lon_all[lo]
print('grid', len(li), len(lo), latv[[0,-1]], lonv[[0,-1]])
# full daily calendar from 1991-12-27 to 2005-08-31
cal = pd.date_range('1991-12-27','2005-08-31',freq='D')
raw = v.isel(latitude=slice(li[0],li[-1]+1), longitude=slice(lo[0],lo[-1]+1)).sel(time=slice('1991-12-27','2005-08-31'))
rt = pd.to_datetime(raw.time.values).normalize()
data = np.full((len(cal), len(li), len(lo)), np.nan)
pos = cal.get_indexer(rt)
assert (pos>=0).all()
data[pos] = raw.values.astype(np.float64)
ncell = len(li)*len(lo)
flat = data.reshape(len(cal), -1)
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
doys = np.array([doy(d) for d in cal])
base = (cal>=pd.Timestamp('1992-01-01'))&(cal<=pd.Timestamp('2002-12-31'))
bidx = np.where(base)[0]
print('baseline days', len(bidx), cal[bidx[0]].date(), cal[bidx[-1]].date())
thr = np.full((367, ncell), np.nan); clim = np.full((367, ncell), np.nan)
for d in range(1,367):
    if d==60: continue
    Bs = bidx[doys[bidx]==d]
    if len(Bs)==0: continue
    idx=set()
    for b in Bs:
        for k in range(-5,6):
            j=b+k
            if 0<=j<len(cal): idx.add(j)   # calendar is daily, so index shift = day shift
    idx = sorted(idx)
    P = flat[idx]
    thr[d] = np.nanquantile(P, 0.9, axis=0, method='hazen')
    clim[d] = np.nanmean(P, axis=0)
thr[60] = (thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    # a: (367, ncell) with index 0 unused; use days 1..366
    b = a[1:367]
    out = np.zeros_like(b)
    for k in range(-15,16):
        out += np.roll(b, -k, axis=0)
    out /= 31.0
    res = np.full_like(a, np.nan); res[1:367]=out
    return res
thr_s = smooth(thr); clim_s = smooth(clim)
# target period
tgt = (cal>=pd.Timestamp('2005-06-01'))&(cal<=pd.Timestamp('2005-08-31'))
tidx = np.where(tgt)[0]
tdates = cal[tidx]
S = flat[tidx]  # (92, ncell)
sea = np.all(np.isfinite(S), axis=0)
print('target days', len(tidx), tdates[0].date(), tdates[-1].date(), 'sea cells', sea.sum(), 'of', ncell)
td = doys[tidx]
T = thr_s[td]  # (92, ncell)
hot = (S >= T) & sea[None,:] & np.isfinite(T)
mhw = np.zeros_like(hot)
for c in np.where(sea)[0]:
    h = hot[:,c]
    # runs
    runs=[]; i=0; n=len(h)
    while i<n:
        if h[i]:
            j=i
            while j+1<n and h[j+1]: j+=1
            if j-i+1>=5: runs.append([i,j])
            i=j+1
        else: i+=1
    # join runs separated by 1 or 2 non-hot days
    merged=[]
    for r in runs:
        if merged and (r[0]-merged[-1][1]-1) in (1,2):
            merged[-1][1]=r[1]
        else: merged.append(list(r))
    for a,b in merged: mhw[a:b+1,c]=True
active = mhw.any(axis=1)
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append({'onset':str(tdates[i].date()),'end':str(tdates[j].date())})
        i=j+1
    else: i+=1
print('events', events)
print('per-cell mhw days', mhw.sum(), 'active days', active.sum())
os.makedirs('output', exist_ok=True)
import xarray as xr
M = mhw.reshape(len(tidx), len(li), len(lo)).astype(np.uint8)
out = xr.Dataset({'mhw': (('time','lat','lon'), M)},
    coords={'time': tdates.values.astype('datetime64[ns]'), 'lat': latv, 'lon': lonv})
out['mhw'].attrs={'long_name':'marine heatwave mask'}
out.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep = {'region': {'lat_min':LAT0,'lat_max':LAT1,'lon_min':LON0,'lon_max':LON1},
       'baseline_analysed': {'start':'1992-01-01','end':'2002-12-31'},
       'target_analysed': {'start':'2005-06-01','end':'2005-08-31'},
       'events': events, 'complete': True,
       'caveats': 'Region grid cells lat 55.68-56.86, lon 16.46-17.64 (60x60). Land cells (non-finite on target period) set to 0. Thresholds from 1992-2002 pool with +/-5 day windows; 1991-12-27 to 2003-01-05 window extension used via data.'}
json.dump(rep, open('output/report.json','w'), indent=2)
print(json.dumps(rep, indent=2)[:1500])
'''
open('/tmp/mhw.py','w').write(script)
import subprocess
r = subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-3000:])
