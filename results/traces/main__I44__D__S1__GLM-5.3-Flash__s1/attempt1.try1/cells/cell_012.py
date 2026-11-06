import numpy as np, datetime as dt, pickle, time, warnings

data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
with open('/work/pool_idx.pkl','rb') as fh: pool_idx=pickle.load(fh)
d0=dates[0]

t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
target=data[ti0:ti1+1]
sea=np.isfinite(target).all(axis=0)

CUM_LEAP=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d): return int(CUM_LEAP[d.month-1]+d.day)

thr_raw=np.full((367,60,60), np.nan)
clim_raw=np.full((367,60,60), np.nan)
t0=time.time()
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in range(1,367):
        if d==60: continue
        v=data[pool_idx[d]].reshape(len(pool_idx[d]),-1)
        thr_raw[d]=np.nanpercentile(v,90,axis=0,method='hazen').reshape(60,60)
        clim_raw[d]=np.nanmean(v,axis=0).reshape(60,60)
print('pool quantile+mean seconds:', time.time()-t0)
thr_raw[60]=0.5*(thr_raw[59]+thr_raw[61])
clim_raw[60]=0.5*(clim_raw[59]+clim_raw[61])
np.savez_compressed('/work/raw.npz', thr_raw=thr_raw[1:], clim_raw=clim_raw[1:])
print('raw saved. sea-finite checks:',
      bool(np.isfinite(thr_raw[1:].reshape(366,-1)[:, sea.ravel()]).all()),
      bool(np.isfinite(clim_raw[1:].reshape(366,-1)[:, sea.ravel()]).all()))

# ---- circular 31-day centred moving mean (366-point wrap)
def circ_smooth(a):
    # a: (366, ...) 0-based doy index
    trip=np.concatenate([a,a,a],axis=0)
    c=np.cumsum(trip,axis=0)
    out=np.empty_like(a)
    for k in range(366):
        lo=k+366-15
        hi=k+366+15
        s=c[hi]-c[lo-1]
        out[k]=s/31.0
    return out
# brute-force validation on random data
rng=np.random.default_rng(0)
a=rng.random((366,3,2))
sm=circ_smooth(a)
ok=True
for k in [0,1,14,15,180,350,364,365]:
    for c1 in range(3):
        for c2 in range(2):
            idxs=[(k+o)%366 for o in range(-15,16)]
            bf=a[idxs,c1,c2].mean()
            if not np.isclose(sm[k,c1,c2],bf,rtol=0,atol=1e-12): ok=False
print('smoother validated vs brute force:', ok)
print('window length check:', (0-15)%366, (365+15)%366)  # wrap examples
