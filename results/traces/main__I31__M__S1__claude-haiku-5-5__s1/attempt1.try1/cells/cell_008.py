analysis = r'''
import numpy as np, pandas as pd, xarray as xr, json, os, datetime as dt
os.makedirs('/tmp/output',exist_ok=True)
C=np.load('/tmp/cache.npz')
sst=C['sst']; dates=pd.to_datetime(C['dates']); la=C['lat']; lo=C['lon']
ny,nx=sst.shape[1:]
idx={d:i for i,d in enumerate(dates)}
def doy(ts):
    return datetime_doy(ts)
def datetime_doy(ts):
    return pd.Timestamp(2000,ts.month,ts.day).dayofyear  # leap template: Feb29=60
# target
tgt=pd.date_range('2017-06-01','2017-08-31')
tidx=[idx[t] for t in tgt]
T=sst[tidx]                       # (92,ny,nx)
sea=np.all(np.isfinite(T),axis=0)  # sea cells
print('sea cells',sea.sum(),'of',ny*nx)
# baseline
base=pd.date_range('1992-01-01','2002-12-31')
pool_dates={d:set() for d in range(1,367)}
for b in base:
    dd=datetime_doy(b)
    if dd==60: continue
    for k in range(-5,6):
        pool_dates[dd].add(b+pd.Timedelta(days=k))
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    ii=[idx[t] for t in sorted(pool_dates[d])]
    P=sst[ii]
    thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a: (366,...) days 1..366 at index 0..365
    out=np.empty_like(a)
    for d in range(366):
        ids=[(d+k)%366 for k in range(-15,16)]
        out[d]=np.mean(a[ids],axis=0)
    return out
thr366=smooth(thr[1:367]); clim366=smooth(clim[1:367])
# hot days
tdoy=np.array([datetime_doy(t) for t in tgt])
th=thr366[tdoy-1]
with np.errstate(invalid='ignore'):
    hot=(T>=th)
hot=hot & sea[None]
# per-cell MHW
mhw=np.zeros(T.shape,dtype=bool)
nt=T.shape[0]
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        h=hot[:,y,x]
        ev=[]; i=0
        while i<nt:
            if h[i]:
                j=i
                while j+1<nt and h[j+1]: j+=1
                if j-i+1>=5: ev.append([i,j])
                i=j+1
            else: i+=1
        merged=[]
        for e in ev:
            if merged and e[0]-merged[-1][1]-1<=2: merged[-1][1]=e[1]
            else: merged.append(list(e))
        for s,e in merged: mhw[s:e+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[]; i=0
while i<nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        events.append({"onset":str(tgt[i].date()),"end":str(tgt[j].date())})
        i=j+1
    else: i+=1
print('events',events)
print('mhw cell-days',mhw.sum(), 'max cells/day',mhw.sum(axis=(1,2)).max())
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
  coords={'time':tgt.values,'lat':la,'lon':lo})
ds['mhw'].attrs={'long_name':'marine heatwave mask'}
ds.to_netcdf('/tmp/output/mhw_mask.nc')
rep={"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2017-06-01","end":"2017-08-31"},
 "events":events,"complete":True,
 "caveats":"Land/ice cells with NaN in baseline pool get NaN threshold and are never hot. Sea cells defined by target period only. Region has 60x60 cells (lat 58.70-59.88, lon 18.70-19.88, all within bounds)."}
json.dump(rep,open('/tmp/output/report.json','w'),indent=2)
print('written')
'''
open('/tmp/analysis.py','w').write(analysis)
import subprocess,time
time.sleep(120)
print(subprocess.run("cat /tmp/extract.log; ls -la /tmp/cache.npz; ps aux | grep extract | head -3",shell=True,capture_output=True,text=True).stdout)