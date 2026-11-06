import numpy as np, datetime as dt, pickle, time, warnings

data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
with open('/work/pool_idx.pkl','rb') as fh: pool_idx=pickle.load(fh)
d0=dates[0]; N=len(dates)

# target slice
t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
target=data[ti0:ti1+1]                      # (92,60,60)
sea=np.isfinite(target).all(axis=0)         # (60,60) bool
print('sea cells:', int(sea.sum()))

CUM_LEAP=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d): return int(CUM_LEAP[d.month-1]+d.day)

# ---- per-doy pools -> hazen p90 and mean, per cell (vectorised over all 3600 cells)
thr_raw=np.full((367,60,60), np.nan)   # index 1..366 used
clim_raw=np.full((367,60,60), np.nan)
t0=time.time()
with warnings.catch_warnings():
    warnings.simplefilter('ignore')  # all-NaN slices (land cells) expected
    for d in range(1,367):
        if d==60: continue
        vals=data[pool_idx[d]]                       # (121,60,60) float64
        v=vals.reshape(vals.shape[0],-1)             # (121,3600)
        q=np.nanpercentile(v, 90, axis=0, method='hazen')
        m=np.nanmean(v, axis=0)
        thr_raw[d]=q.reshape(60,60)
        clim_raw[d]=m.reshape(60,60)
el=time.time()-t0
print('pools quantile+mean seconds:', el)

# land cells all-NaN?
print('land cells thr all NaN:', bool(np.isnan(thr_raw[1:][~sea]).all()), ' sea cells thr all finite:', bool(np.isfinite(thr_raw[1:][:, sea]).all()))
print('sea cells clim all finite:', bool(np.isfinite(clim_raw[1:][:, sea]).all()))

# ---- day 60 := mean of days 59 and 61
thr_raw[60]=0.5*(thr_raw[59]+thr_raw[61])
clim_raw[60]=0.5*(clim_raw[59]+clim_raw[61])
print('day60 filled; sea all finite now:', bool(np.isfinite(thr_raw[1:][:, sea]).all()), bool(np.isfinite(clim_raw[1:][:, sea]).all()))

# ---- circular 31-day centred moving mean over doy 1..366
def circ_smooth(a):
    # a: (366, ...) indexed 0..365 = doy 1..366
    c=np.cumsum(np.concatenate([a, a, a], axis=0), axis=0)   # (1098,...)
    half=15
    out=np.empty_like(a)
    for k in range(366):
        lo=k+365-half      # index of doy k-15 in the tripled array (0-based): (k-15)+366
        hi=k+366+half      # inclusive end: (k+15)+366
        out[k]=(c[hi]-c[lo-1])/31.0 if lo>0 else (c[hi]-c[0]+a[0])/31.0  # lo>=365>0 always here
    return out
thr_sm=np.full((367,60,60), np.nan); clim_sm=np.full((367,60,60), np.nan)
thr_sm[1:]=circ_smooth(thr_raw[1:])
clim_sm[1:]=circ_smooth(clim_raw[1:])
print('smoothed; sea finite:', bool(np.isfinite(thr_sm[1:][:, sea]).all()), bool(np.isfinite(clim_sm[1:][:, sea]).all()))

# ---- hot days in target period: sst >= thr[doy]
hot=np.zeros(target.shape, dtype=bool)
for k in range(target.shape[0]):
    d=doy_of(t_start+dt.timedelta(days=k))
    hot[k]=target[k]>=thr_sm[d]
print('hot day-cell fraction:', hot[:, sea].mean())
print('hot days per cell min/max (sea):', hot[:,sea].sum(axis=0).min(), hot[:,sea].sum(axis=0).max())

np.savez_compressed('/work/thr_clim.npz', thr_raw=thr_raw[1:], clim_raw=clim_raw[1:], thr_sm=thr_sm[1:], clim_sm=clim_sm[1:], sea=sea, hot=hot)
print('saved thr_clim.npz')
