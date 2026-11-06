
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, json
z=np.load('/work/sub.npz')
sst=z['sst']; dates=pd.DatetimeIndex(z['time'].astype('datetime64[D]')); lat=z['lat']; lon=z['lon']
def doy_of(ts):
    m=np.asarray(ts.month); dd=np.asarray(ts.day)
    ref=pd.DatetimeIndex([pd.Timestamp(2000,int(a),int(b)) for a,b in zip(m,dd)])
    return ref.dayofyear.values.astype(int)   # leap reference: Feb29=60, Mar1=61, Dec31=366
print(doy_of(pd.DatetimeIndex(['2001-02-28','2000-02-29','2001-03-01','2001-12-31','2000-12-31'])))
dmap={dt:i for i,dt in enumerate(dates)}
base_B=pd.date_range('1992-01-01','2002-12-31')
bd=doy_of(base_B)
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
cnt={}
for d in range(1,367):
    if d==60: continue
    Bs=base_B[(bd==d)]
    vals=[sst[dmap[b+pd.Timedelta(days=k)]] for b in Bs for k in range(-5,6)]
    P=np.stack(vals).reshape(len(vals),-1)
    cnt[d]=(len(Bs),P.shape[0])
    thr[d]=np.nanpercentile(P,90,axis=0,method='hazen').reshape(60,60)
    clim[d]=np.nanmean(P,axis=0).reshape(60,60)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a: (366,...) index doy-1
    out=np.empty_like(a)
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[idx],axis=0)
    return out
thr_s=smooth(thr[1:]); clim_s=smooth(clim[1:])
print(sorted(set(cnt.values()))[:5], len(set(cnt.values())), np.isnan(thr_s).sum(), np.isnan(clim_s).sum())
