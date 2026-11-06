
script = r'''
import xarray as xr, numpy as np, pandas as pd, json, os
os.makedirs('output',exist_ok=True)
ds = xr.open_dataset('/work/sst.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=59.05)&(lat<=60.25))[0]; lo=np.where((lon>=21.25)&(lon<=22.45))[0]
sub = ds.analysed_sst.sel(time=slice('1991-12-27','2005-08-31')).isel(latitude=la, longitude=lo).load()
A = sub.values.astype(np.float64); t = pd.DatetimeIndex(sub.time.values)
latv = sub.latitude.values; lonv = sub.longitude.values
cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
D = np.array([60 if (d.month==2 and d.day==29) else cum[d.month-1]+d.day for d in t])
assert D.max()==366 and D[t==pd.Timestamp('2001-12-31')][0]==366 and D[t==pd.Timestamp('2001-03-01')][0]==61
ndates=len(t)
centre_idx = np.where((t>=pd.Timestamp('1992-01-01'))&(t<=pd.Timestamp('2002-12-31')))[0]
thr = np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
psz={}
for d in range(1,367):
    if d==60: continue
    cs = centre_idx[D[centre_idx]==d]
    m = np.zeros(ndates,bool)
    for c in cs:
        m[max(c-5,0):min(c+5,ndates-1)+1]=True
    pool=A[m]; psz[d]=pool.shape[0]
    thr[d]=np.quantile(pool,0.9,axis=0,method='hazen')
    clim[d]=pool.mean(axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):
    # x: (367,...) index 1..366 used; build 366 array
    arr = x[1:367]
    out=np.empty_like(arr)
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i]=arr[idx].mean(axis=0)
    return out
thrS = smooth(thr)   # index i -> doy i+1
climS = smooth(clim)
print('pool sizes min/max', min(psz.values()), max(psz.values()))
# target
tm = (t>=pd.Timestamp('2005-06-01'))&(t<=pd.Timestamp('2005-08-31'))
ti = np.where(tm)[0]
T = A[ti]; Dt = D[ti]; dates = t[ti]
sea = np.all(np.isfinite(T),axis=0)
print('sea cells', sea.sum(), 'target days', len(ti))
thr_t = thrS[Dt-1]  # (ntarget,60,60)
hot = (T >= thr_t) & sea[None]
ntime=len(ti)
mhw = np.zeros((ntime,60,60),bool)
for iy in range(60):
    for ix in range(60):
        if not sea[iy,ix]: continue
        h = hot[:,iy,ix]
        # qualifying runs
        runs=[]; i=0
        while i<ntime:
            if h[i]:
                j=i
                while j+1<ntime and h[j+1]: j+=1
                if j-i+1>=5: runs.append([i,j])
                i=j+1
            else: i+=1
        # join
        segs=[]
        for r in runs:
            if segs and (r[0]-segs[-1][1]-1) in (1,2) and not h[segs[-1][1]+1:r[0]].any():
                segs[-1][1]=r[1]
            else: segs.append(list(r))
        for s,e in segs: mhw[s:e+1,iy,ix]=True
active = mhw.any(axis=(1,2))
events=[]; i=0
while i<ntime:
    if active[i]:
        j=i
        while j+1<ntime and active[j+1]: j+=1
        events.append({'onset':str(dates[i].date()),'end':str(dates[j].date())})
        i=j+1
    else: i+=1
print('events', events)
# outputs
full = np.zeros((ntime,60,60),np.uint8); full[:]=mhw.astype(np.uint8)
out = xr.Dataset({'mhw':(('time','lat','lon'), full)},
    coords={'time':dates.values,'lat':latv,'lon':lonv})
out['mhw'].attrs={'long_name':'marine heatwave flag per cell'}
out.to_netcdf('output/mhw_mask.nc')
report={'region':{'lat_min':59.05,'lat_max':60.25,'lon_min':21.25,'lon_max':22.45},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':str(dates[0].date()),'end':str(dates[-1].date())},
 'events':events,'complete':True,
 'caveats':'Land cells (all-NaN) are 0. Baseline pool uses calendar-window union of +-5 days with extension dates 1991-12-27..31 and 2003-01-01..05. Joining of MHWs: gap of 1-2 days between qualifying runs joined only if all gap days non-hot. Region-wide events from union of per-cell MHW days. Full 1982-2023 file not used beyond needed span.'}
json.dump(report, open('output/report.json','w'), indent=2)
print('written; mhw sum', int(mhw.sum()), 'sea cells in MHW any day', int(mhw.any(axis=0).sum()))
'''
open('/work/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/run.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout[-6000:], r.stderr[-3000:])
