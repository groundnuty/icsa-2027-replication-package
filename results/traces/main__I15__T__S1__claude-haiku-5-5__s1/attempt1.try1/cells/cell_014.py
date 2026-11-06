
import numpy as np, datetime as dt, json, os, warnings
import xarray as xr
warnings.filterwarnings('ignore')
Z=np.load('/tmp/sst_region.npz')
arr=Z['sst']; dstr=Z['dates']; rlat=Z['lat']; rlon=Z['lon']
D=[dt.date.fromisoformat(s) for s in dstr]
def doy2(x):
    if x.month==2 and x.day==29: return 60
    nl=[0,31,59,90,120,151,181,212,243,273,304,334][x.month-1]+x.day
    return nl+1 if x.month>=3 else nl
idx={d:i for i,d in enumerate(D)}
nlat,nlon=arr.shape[1:]
tgt=[i for i,d in enumerate(D) if dt.date(2019,6,1)<=d<=dt.date(2019,8,31)]
tdates=[D[i] for i in tgt]
sea=np.all(np.isfinite(arr[tgt]),axis=0)
pools={d:[] for d in range(1,367) if d!=60}
b=dt.date(1992,1,1)
while b<=dt.date(2002,12,31):
    dd=doy2(b)
    if dd!=60:
        for k in range(-5,6):
            D2=b+dt.timedelta(k)
            if D2 in idx: pools[dd].append(idx[D2])
    b+=dt.timedelta(1)
thr=np.full((366,nlat,nlon),np.nan); clim=np.full((366,nlat,nlon),np.nan)
for d in range(1,367):
    if d==60: continue
    v=arr[pools[d]]
    thr[d-1]=np.nanquantile(v,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(v,axis=0)
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        out[d]=np.mean(a[[(d+k)%366 for k in range(-15,16)]],axis=0)
    return out
thrS=smooth(thr)
hot=np.zeros((len(tgt),nlat,nlon),bool)
for j,i in enumerate(tgt):
    hot[j]=arr[i]>=thrS[doy2(D[i])-1]
hot &= sea[None]
T=len(tgt)
mhw=np.zeros_like(hot)
for y in range(nlat):
    for x in range(nlon):
        if not sea[y,x]: continue
        h=hot[:,y,x]
        runs=[]; s=None
        for t_ in range(T+1):
            v=h[t_] if t_<T else False
            if v and s is None: s=t_
            if not v and s is not None:
                if t_-s>=5: runs.append([s,t_-1])
                s=None
        if not runs: continue
        merged=[runs[0][:]]
        for r in runs[1:]:
            if r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
            else: merged.append(r[:])
        for a_,b_ in merged: mhw[a_:b_+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[]; s=None
for t_ in range(T+1):
    v=active[t_] if t_<T else False
    if v and s is None: s=t_
    if not v and s is not None:
        events.append({'onset':tdates[s].isoformat(),'end':tdates[t_-1].isoformat()}); s=None
print(events, int(mhw.sum()))
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
              coords={'time':('time',np.array([np.datetime64(d) for d in tdates],dtype='datetime64[ns]')),
                      'lat':('lat',rlat.astype(np.float32)),'lon':('lon',rlon.astype(np.float32))})
ds['mhw'].encoding={'dtype':'uint8'}
ds.to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':56.13,'lat_max':57.33,'lon_min':17.71,'lon_max':18.91},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2019-06-01','end':'2019-08-31'},
     'events':events,'complete':True,
     'caveats':'Region grid cells 56.14-57.32 N, 17.72-18.90 E (0.02 deg grid). 3300 of 3600 cells are sea cells (finite on all target days); other cells set to 0 and excluded. Day-60 threshold/climatology = mean of days 59 and 61 before smoothing. SST used as stored (float32 K, cast to float64).'}
json.dump(rep,open('output/report.json','w'),indent=2)
chk=xr.open_dataset('output/mhw_mask.nc'); print(chk.mhw.dtype, chk.mhw.shape, int(chk.mhw.sum()))
