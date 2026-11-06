
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, json, xarray, os
z=np.load('/work/sub.npz')
sst=z['sst']; dates=pd.DatetimeIndex(z['time'].astype('datetime64[D]')); lat=z['lat']; lon=z['lon']
def doy_of(ts):
    m=np.asarray(ts.month); dd=np.asarray(ts.day)
    ref=pd.DatetimeIndex([pd.Timestamp(2000,int(a),int(b)) for a,b in zip(m,dd)])
    return ref.dayofyear.values.astype(int)
dmap={dt:i for i,dt in enumerate(dates)}
base_B=pd.date_range('1992-01-01','2002-12-31'); bd=doy_of(base_B)
thr=np.full((367,60,60),np.nan)
for d in range(1,367):
    if d==60: continue
    Bs=base_B[(bd==d)]
    P=np.stack([sst[dmap[b+pd.Timedelta(days=k)]] for b in Bs for k in range(-5,6)]).reshape(-1,3600)
    thr[d]=np.nanpercentile(P,90,axis=0,method='hazen').reshape(60,60)
thr[60]=(thr[59]+thr[61])/2
def smooth(a):
    out=np.empty_like(a)
    for i in range(366):
        out[i]=np.mean(a[[(i+k)%366 for k in range(-15,16)]],axis=0)
    return out
thr_s=smooth(thr[1:])
# target
tgt=np.where((dates>=pd.Timestamp('2020-06-01'))&(dates<=pd.Timestamp('2020-08-31')))[0]
T=sst[tgt]; td=dates[tgt]; tdoy=doy_of(td)
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'target days',len(tgt), td[0].date(), td[-1].date())
th=thr_s[tdoy-1]  # (ndays,60,60)
hot=(T>=th)&sea[None]
hot=hot&np.isfinite(th)
def runs(b):
    # return mask of qualifying per-cell MHWs with 1-2 day gap joining
    n=len(b); m=np.zeros(n,bool)
    i=0; rl=[]
    while i<n:
        if b[i]:
            j=i
            while j<n and b[j]: j+=1
            if j-i>=5: rl.append([i,j-1])
            i=j
        else: i+=1
    for r in rl: m[r[0]:r[1]+1]=True
    # join
    for k in range(len(rl)-1):
        gap=rl[k+1][0]-rl[k][1]-1
        if gap in (1,2): m[rl[k][1]+1:rl[k+1][0]]=True
    return m
mhw=np.zeros(hot.shape,np.uint8)
for a in range(60):
    for o in range(60):
        if sea[a,o] and hot[:,a,o].any():
            mhw[:,a,o]=runs(hot[:,a,o])
active=mhw.reshape(len(tgt),-1).any(axis=1)
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j<n and active[j]: j+=1
        events.append({"onset":td[i].strftime('%Y-%m-%d'),"end":td[j-1].strftime('%Y-%m-%d')}); i=j
    else: i+=1
print(events); print('cell-days MHW',mhw.sum(), 'active days',active.sum())
