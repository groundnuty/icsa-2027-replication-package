
import xarray as xr, numpy as np, pandas as pd, json, os
d=np.load('/tmp/w/d.npz')
base=d['base']; btime=pd.to_datetime(d['btime']); tv=d['tv']; ttime=pd.to_datetime(d['ttime']); latv=d['lat']; lonv=d['lon']
ny,nx=base.shape[1:]
ref=pd.date_range('2000-01-01','2000-12-31')
md2doy={(t.month,t.day):t.day_of_year for t in ref}
doy_of=lambda idx: np.array([md2doy[(t.month,t.day)] for t in idx])
bdoy=doy_of(btime); tdoy=doy_of(ttime)
sea=np.isfinite(tv).all(axis=0)
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
import warnings; warnings.filterwarnings('ignore')
for doy in range(1,367):
    if doy==60: continue
    md=ref[doy-1]
    pool=[]
    for y in range(1992,2003):
        s=pd.Timestamp(year=y,month=md.month,day=md.day)
        pool.append(np.where((btime>=s-pd.Timedelta(days=5))&(btime<=s+pd.Timedelta(days=5)))[0])
    idx=np.unique(np.concatenate(pool))
    P=base[idx]
    thr[doy]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[doy]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]; out=np.empty_like(a)
    for i in range(366):
        out[i]=a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0)
    return out
T=smooth(thr)
Tt=T[tdoy-1]
hot=(tv>=Tt)&sea[None]
def runs(b):
    r=[];i=0;n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
nt=len(ttime); mhw=np.zeros((nt,ny,nx),bool)
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        rr=[r for r in runs(hot[:,y,x]) if r[1]-r[0]+1>=5]
        if not rr: continue
        groups=[list(rr[0])]
        for s,e in rr[1:]:
            if s-groups[-1][1]-1<=2: groups[-1][1]=e
            else: groups.append([s,e])
        for s,e in groups: mhw[s:e+1,y,x]=True
active=mhw.any(axis=(1,2))
ev=[];i=0
while i<nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        ev.append({"onset":str(ttime[i].date()),"end":str(ttime[j].date())}); i=j+1
    else: i+=1
print('hot',hot.sum(),'mhw',mhw.sum(),'active',active.sum(), 'sea',sea.sum())
print(ev)
