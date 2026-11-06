
import pandas as pd, json, os
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
def doy(dates):
    # fixed leap-year mapping
    d2000=pd.to_datetime(dict(year=2000,month=dates.month,day=dates.day))
    return (d2000.dayofyear).values  # 2000 is leap: Feb29=60, Mar1=61
bdoy=doy(bt); tdoy=doy(tt)
B=b.values.astype(np.float64)  # (T,lat,lon)
ny,nx=B.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
base_start=bt.min(); base_end=pd.Timestamp('2002-12-31')
bd_in=(bt>=pd.Timestamp('1992-01-01'))&(bt<=base_end)
for d in range(1,367):
    if d==60: continue
    Ds=bt[bd_in & (bdoy==d)]
    if len(Ds)==0: continue
    idx=set()
    for D in Ds:
        lo_=D-pd.Timedelta(days=5); hi_=D+pd.Timedelta(days=5)
        m=np.where((bt>=lo_)&(bt<=hi_))[0]
        idx.update(m.tolist())
    idx=sorted(idx)
    pool=B[idx]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a1=a[1:367]  # days 1..366 -> index 0..365
    out=np.empty_like(a1)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a1[ids],axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)  # index d-1
# Check: pool for day 60 excluded; baseline years all present
print(np.isnan(thrS).all(axis=0).sum(), np.isnan(thrS).sum())
