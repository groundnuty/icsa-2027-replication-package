
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, json
z=np.load('/work/sub.npz')
sst=z['sst']; dates=pd.DatetimeIndex(z['time'].astype('datetime64[D]')); lat=z['lat']; lon=z['lon']
def doy_of(ts):
    m=np.asarray(ts.month); dd=np.asarray(ts.day)
    ref=pd.DatetimeIndex([pd.Timestamp(2001,int(a),int(b)) if not (a==2 and b==29) else pd.Timestamp(2001,2,28) for a,b in zip(m,dd)])
    out=ref.dayofyear.values.astype(int)
    out[(m==2)&(dd==29)]=60
    return out
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
def smooth(a):
    a=a[1:]  # days 1..366 -> index 0..365
    out=np.empty_like(a)
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[idx],axis=0)
    return out
thr_s=smooth(thr[1:]); clim_s=smooth(clim[1:])  # shape (366,60,60), index doy-1
print(set(cnt.values()), np.isnan(thr_s).sum(), np.isnan(clim_s).sum())
np.savez('/work/thr.npz',thr=thr_s,clim=clim_s)
