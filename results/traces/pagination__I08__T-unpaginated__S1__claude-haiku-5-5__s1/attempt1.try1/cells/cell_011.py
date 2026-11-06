script = r'''
import numpy as np, pandas as pd, json, os, xarray as xr
Z=np.load('/tmp/x/cache.npz'); arr=Z['arr']; la=Z['la']; lo=Z['lo']; alld=pd.to_datetime(Z['dates'])
ndays=len(alld)
def doy_of(ts):
    if ts.month==2 and ts.day==29: return 60
    doy=pd.Timestamp(2001, ts.month, ts.day).day_of_year
    if doy>=60: doy+=1
    return doy
assert doy_of(pd.Timestamp('2004-02-29'))==60 and doy_of(pd.Timestamp('2004-03-01'))==61 and doy_of(pd.Timestamp('2004-12-31'))==366 and doy_of(pd.Timestamp('2004-02-28'))==59
doys=np.array([doy_of(t) for t in alld])
base_mask=(alld>=pd.Timestamp('1992-01-01'))&(alld<=pd.Timestamp('2002-12-31'))
ncell=arr.shape[1]*arr.shape[2]
flat=arr.reshape(ndays,-1)
thr=np.full((367,ncell),np.nan); clim=np.full((367,ncell),np.nan)
bdates=alld[base_mask]
bdoy=np.array([doy_of(t) for t in bdates])
for d in range(1,367):
    if d==60: continue
    bd=bdates[bdoy==d]
    if len(bd)==0: continue
    sel=np.zeros(ndays,bool)
    for b in bd:
        sel |= (alld>=b-pd.Timedelta(days=5))&(alld<=b+pd.Timedelta(days=5))
    pool=flat[sel]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    with np.errstate(all='ignore'):
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    out=np.full_like(a,np.nan); v=a[1:367]
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i+1]=np.mean(v[idx],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
tmask=(alld>=pd.Timestamp('2007-06-01'))&(alld<=pd.Timestamp('2007-08-31'))
tidx=np.where(tmask)[0]; tday=alld[tidx]
T=arr[tidx]
sea=np.all(np.isfinite(T),axis=0).reshape(-1)
print('sea cells', sea.sum(), 'of', ncell, 'ntarget', len(tidx))
Tf=T.reshape(len(tidx),-1)
thr_t=thr_s[doys[tidx]]
with np.errstate(invalid='ignore'):
    hot=(Tf>=thr_t)&np.isfinite(thr_t)
hot &= sea[None,:]
def cell_mhw(h):
    n=len(h); m=np.zeros(n,bool); runs=[]; i=0
    while i<n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            if j-i>=5: runs.append([i,j-1])
            i=j
        else: i+=1
    merged=[]
    for r in runs:
        if merged and (r[0]-merged[-1][1]-1) in (1,2): merged[-1][1]=r[1]
        else: merged.append(list(r))
    for a,b in merged: m[a:b+1]=True
    return m
M=np.zeros_like(hot)
for c in np.where(sea)[0]: M[:,c]=cell_mhw(hot[:,c])
active=M.any(axis=1)
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j<n and active[j]: j+=1
        events.append({"onset":tday[i].strftime('%Y-%m-%d'),"end":tday[j-1].strftime('%Y-%m-%d')}); i=j
    else: i+=1
print(events); print('active days', int(active.sum()), 'cells ever', int(M.any(0).sum()))
print('hot cells-days', int(hot.sum()), 'thr nan in sea', int(np.isnan(thr_t[:,sea]).sum()))
os.makedirs('output',exist_ok=True)
mask3=M.reshape(len(tidx),arr.shape[1],arr.shape[2]).astype(np.uint8)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mask3)},
  coords={'time':('time',tday.values.astype('datetime64[ns]')),'lat':('lat',la),'lon':('lon',lo)})
ds.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":54.81,"lat_max":56.01,"lon_min":19.61,"lon_max":20.81},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2007-06-01","end":"2007-08-31"},
 "events":events,"complete":True,
 "caveats":"Grid cells selected by float32 coordinate tolerance (1e-4): 60x60 cells lat 54.82-56.00, lon 19.62-20.80. Baseline windows use calendar +-5 days, including 1991-12-27..31 and 2003-01-01..05. Non-sea cells (non-finite SST on any target day) set to 0. Thresholds use float64 hazen quantile over pools with NaN removed."}
json.dump(rep,open('output/report.json','w'),indent=2)
print('written')
'''
open('/tmp/x/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/x/run.py'],capture_output=True,text=True,cwd='/tmp/x')
print(r.stdout[-4000:], r.stderr[-3000:])
