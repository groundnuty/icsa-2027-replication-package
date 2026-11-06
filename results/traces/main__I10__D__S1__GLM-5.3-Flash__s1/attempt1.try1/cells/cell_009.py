import numpy as np, datetime as dt, json, warnings, time
warnings.filterwarnings('ignore')

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def mdoy(y,m,d): return CUM[m-1]+d

Barr = np.load('/work/baseline_sst.npy')          # (4028,60,60) float64
T    = np.load('/work/target_sst.npy')            # (92,60,60) float64
tstr = np.load('/work/target_datestr.npy')
ext_start = dt.date(1991,12,27)
nd = Barr.shape[0]
cdates = [ext_start + dt.timedelta(i) for i in range(nd)]
mdoy_all = np.array([mdoy(c.year,c.month,c.day) for c in cdates])   # 1..366
is_baseline = np.array([(dt.date(1992,1,1) <= c <= dt.date(2002,12,31)) for c in cdates])
print('candidates:', nd, '| baseline centers:', is_baseline.sum())
assert mdoy_all[0]==361 and mdoy_all[4]==365 and mdoy_all[5]==1 and mdoy_all[-1]==5

# ---- pools per day of year ----
thr = np.full((366,)+Barr.shape[1:], np.nan)
clim = np.full_like(thr, np.nan)
pool_sizes = []
t0=time.time()
for d in range(1,367):
    if d==60: continue
    ci = np.flatnonzero(is_baseline & (mdoy_all==d))          # baseline center indices
    assert ci.size>0
    lo, hi = max(ci.min()-5,0), min(ci.max()+5, nd-1)
    # union of windows [i-5,i+5] over centers (contiguous per center; centers are far apart)
    idx = np.unique(np.concatenate([np.arange(max(i-5,0), min(i+5,nd-1)+1) for i in ci]))
    pool = Barr[idx]                                          # (n,60,60)
    pool_sizes.append((d, ci.size, idx.size))
    thr[d-1]  = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(pool, axis=0)
print('pools+quantiles done in', round(time.time()-t0,1),'s')
ps = np.array([p[2] for p in pool_sizes])
print('pool sizes: min', ps.min(), 'max', ps.max(), 'mean', round(ps.mean(),1))
# Feb 29 values must appear in pools of calendar neighbours, not day 60:
feb29_idx = np.flatnonzero([(c.month==2 and c.day==29) for c in cdates])
print('Feb29 candidate days:', [str(cdates[i]) for i in feb29_idx])
# check day-59 pool contains Feb 29 1996 (window of Feb 28 1996 ±5)
ci59 = np.flatnonzero(is_baseline & (mdoy_all==59))
w59 = set()
for i in ci59:
    w59.update(range(max(i-5,0), min(i+5,nd-1)+1))
print('Feb29 in d59 pool:', all(i in w59 for i in feb29_idx))
ci61 = np.flatnonzero(is_baseline & (mdoy_all==61)); w61=set()
for i in ci61: w61.update(range(max(i-5,0), min(i+5,nd-1)+1))
print('Feb29 in d61 pool:', all(i in w61 for i in feb29_idx))
print('Feb29 never a center (d60 skipped):', True)

# ---- day 60 = mean of days 59 and 61 ----
thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print('day60 filled; any NaN in thr rows 59-61 (sea cells)?', np.isnan(thr[58:61]).any())

# ---- 31-day centred moving mean, wrap mod 366 ----
def smooth31(a):   # a: (366,60,60)
    p = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(p, axis=0)
    s = c[30:].copy()
    s[1:] = c[30:] - c[:-31]
    return s/31.0
thr_s = smooth31(thr); clim_s = smooth31(clim)
print('smoothed. check wrap: mean of days 352..366,1..15 == thr_s[365]?',
      np.allclose(thr_s[365], np.concatenate([thr[351:], thr[:15]]).mean(axis=0)))

# ---- sea cells ----
sea = np.isfinite(T).all(axis=0)     # (60,60)
print('sea cells:', sea.sum(), 'of', sea.size)
print('sea-cell baseline NaN days max:', np.isnan(Barr[:,sea]).sum(axis=0).max())
print('thr/clim NaN on sea cells:', np.isnan(thr_s[:,sea]).sum(), np.isnan(clim_s[:,sea]).sum())

# ---- hot days over target period ----
tdoy = np.array([mdoy(int(s[:4]),int(s[4:6]),int(s[6:])) for s in tstr])
print('target doys:', tdoy[0], '->', tdoy[-1], 'contiguous:', np.all(np.diff(tdoy)==1))
hot = np.zeros(T.shape, bool)
for t in range(T.shape[0]):
    hot[t] = T[t] >= thr_s[tdoy[t]-1]
print('hot day-cells on sea cells:', int(hot[:,sea].sum()), '/', sea.sum()*T.shape[0],
      '=', round(hot[:,sea].sum()/(sea.sum()*92)*100,2), '%')
np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s); np.save('/work/hot.npy', hot)
np.save('/work/sea.npy', sea)
# sample diagnostics: cell (30,30)
print('sample cell (30,30) sea?', sea[30,30], 'T Jun1..5:', T[:5,30,30].round(2))
print('  thr doy153..157:', thr_s[152:157,30,30].round(2), 'clim:', clim_s[152:157,30,30].round(2))
