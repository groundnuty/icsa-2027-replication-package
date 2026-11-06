code = r'''
import numpy as np, pandas as pd, xarray as xr, json, os, warnings
warnings.filterwarnings('ignore')
z=np.load('/tmp/sst.npz')
A=z['A']; dates=pd.to_datetime(z['dates']); lat=z['lat']; lon=z['lon']
idx={d:i for i,d in enumerate(dates)}
def doy(t):
    t=pd.Timestamp(t)
    return pd.Timestamp(2000,t.month,t.day).dayofyear  # leap-style: Feb29=60, Mar1=61, non-leap Mar+ shifted
ntime,nlat,nlon=A.shape
bstart=pd.Timestamp('1992-01-01'); bend=pd.Timestamp('2002-12-31')
pools={k:[] for k in range(1,367)}
for c in pd.date_range(bstart,bend):
    dd=doy(c)
    if dd==60: continue
    for k in range(-5,6):
        t=c+pd.Timedelta(days=k)
        pools[dd].append(A[idx[t]])
thr=np.full((367,nlat,nlon),np.nan); clim=np.full((367,nlat,nlon),np.nan)
for dd in range(1,367):
    if dd==60: continue
    P=np.concatenate(pools[dd],axis=0)  # (n,lat,lon)
    thr[dd]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(X):
    Y=np.empty_like(X)
    days=np.arange(1,367)
    for d_ in days:
        ks=[((d_-1+o)%366) for o in range(-15,16)]
        Y[d_]=np.mean(X[[k+1 for k in ks]],axis=0)
    return Y
thr_s=smooth(thr[1:].reshape(366,nlat,nlon) if False else thr) if False else None
# do smoothing on 366-array (index 0 = day1)
T=thr[1:]; C=clim[1:]
def smooth366(X):
    out=np.empty_like(X)
    for d_ in range(366):
        ks=[(d_+o)%366 for o in range(-15,16)]
        out[d_]=np.mean(X[ks],axis=0)
    return out
Ts=smooth366(T); Cs=smooth366(C)
# target
tmask=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
tidx=np.where(tmask)[0]; tdates=dates[tidx]
S=A[tidx]  # (nt,lat,lon)
sea=np.all(np.isfinite(S),axis=0)
print('sea cells',sea.sum(),'of',nlat*nlon, 'target days',len(tdates))
doys=np.array([doy(t) for t in tdates])
thr_t=Ts[doys-1]  # (nt,lat,lon)
hot=(S>=thr_t)&sea[None]
mhw=np.zeros_like(hot)
for i in range(nlat):
    for j in range(nlon):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs
        runs=[]; t=0; n=len(h)
        while t<n:
            if h[t]:
                s=t
                while t<n and h[t]: t+=1
                runs.append([s,t-1])
            else: t+=1
        runs=[r for r in runs if r[1]-r[0]+1>=5]
        # join gaps 1-2
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1)<=2:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<len(active):
    if active[t]:
        s=t
        while t<len(active) and active[t]: t+=1
        events.append({"onset":str(tdates[s].date()),"end":str(tdates[t-1].date())})
    else: t+=1
print('hot cells-days',hot.sum(),'mhw cell-days',mhw.sum())
print('events',events)
os.makedirs('/tmp/output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
   coords={'time':tdates.values,'lat':lat,'lon':lon})
ds.to_netcdf('/tmp/output/mhw_mask.nc')
rep={"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
 "events":events,"complete":True,
 "caveats":"Sea cells = finite on all target days; land/partially-NaN cells are 0 in mask. Threshold/climatology from 1992-2002 pools with +-5 day windows (edge days 1991-12-27..2003-01-05 included). Day-of-year uses leap-style mapping (Feb29=60)."}
json.dump(rep,open('/tmp/output/report.json','w'),indent=2)
print(sea.sum(), mhw.any(axis=0).sum())
'''
open('/tmp/mhw.py','w').write(code)
r=subprocess.run("cd /tmp && python mhw.py", shell=True, capture_output=True, text=True); print(r.stdout, r.stderr[-3000:])