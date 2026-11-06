
import numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
sub=np.load('/tmp/w/sub.npy'); T=pd.DatetimeIndex(pd.read_csv('/tmp/w/T.csv',index_col=0,parse_dates=True).index)
lat=np.load('/tmp/w/lat.npy'); lon=np.load('/tmp/w/lon.npy')

def isleap(y): return (y%4==0 and y%100!=0) or y%400==0
def doy(ts):
    std=ts.dayofyear
    if (not isleap(ts.year)) and std>=60: return std+1
    return std
DOY=np.array([doy(t) for t in T])
pos={t:i for i,t in enumerate(T)}
base_s=pd.Timestamp('1992-01-01'); base_e=pd.Timestamp('2002-12-31')
bases=pd.date_range(base_s,base_e)
pools={}
for b in bases:
    d=doy(b)
    if d==60: continue
    for k in range(-5,6):
        t=b+pd.Timedelta(days=k)
        if t in pos:
            pools.setdefault(d,[]).append(pos[t])
# ensure no duplicate dates per pool
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for d in range(1,367):
    if d==60: continue
    ids=sorted(set(pools[d]))
    vals=sub[ids]
    thr[d]=np.nanpercentile(vals,90,axis=0,method='hazen')
    clim[d]=np.nanmean(vals,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a indexed 1..366 in a[1:]
    x=a[1:367]
    out=np.empty_like(x)
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(x[ii],axis=0)
    r=np.full_like(a,np.nan); r[1:367]=out; return r
thrS=smooth(thr); climS=smooth(clim)
print('pool sizes', {d:len(set(pools[d])) for d in [1,60+1,153,366]} if False else len(set(pools[153])), len(set(pools[1])))

# sea cells
tm=(T>=pd.Timestamp('2012-06-01'))&(T<=pd.Timestamp('2012-08-31'))
tgt_idx=np.where(tm)[0]
tgt=sub[tgt_idx]
sea=np.all(np.isfinite(tgt),axis=0)
print('sea cells', sea.sum(), 'target days', len(tgt_idx))
# baseline nan check for sea cells
print('sea cells with nan threshold', np.sum(sea & ~np.isfinite(thrS[1:367]).all(axis=0)))
