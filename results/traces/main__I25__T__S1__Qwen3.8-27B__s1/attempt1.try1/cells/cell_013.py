
import numpy as np, datetime as dt, time
np.printoptions(precision=4, suppress=True)
sst_base = np.load('/tmp/sst_base.npy')   # (4028, 3600)
sst_tgt  = np.load('/tmp/sst_tgt.npy')    # (92, 3600)
bord = np.load('/tmp/bdates.npy'); tor = np.load('/tmp/tdates.npy')

def doy_of(ordinal):
    d = dt.date.fromordinal(int(ordinal))
    cum = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
    return int(cum[d.month-2]) + d.day if d.month>1 else d.day

t0=time.time()
# day-of-year (1..366, leap-year layout) for every baseline data date
b_doy = np.array([doy_of(o) for o in bord], dtype=np.int64)
t_doy = np.array([doy_of(o) for o in tor], dtype=np.int64)
print("target doys:", t_doy.min(), t_doy.max(), "n:", len(t_doy), "unique:", len(np.unique(t_doy)))

b0 = dt.date(1992,1,1).toordinal(); b1 = dt.date(2002,12,31).toordinal()
print("baseline ordinal range:", b0, b1, "span days:", b1-b0+1)

# For each baseline data date t, contributing baseline dates b in [t-5,t+5] ∩ [b0,b1];
# t contributes to pool_{doy(b)}.
rows_of_doy = {d: [] for d in range(1,367)}
for i, o in enumerate(bord):
    lo = max(int(o)-5, b0); hi = min(int(o)+5, b1)
    for b in range(lo, hi+1):
        rows_of_doy[doy_of(b)].append(i)
sizes = {d: len(v) for d, v in rows_of_doy.items()}
import collections
print("pool row-size histogram:", collections.Counter(sizes.values()))
print("doy 60 rows:", sizes[60])

thr  = np.full(367, np.nan)   # index by doy
clim = np.full(367, np.nan)
for d in range(1,367):
    if d == 60: continue
    idx = rows_of_doy[d]
    pool = sst_base[idx]          # (121, 3600)
    thr[d]  = np.nanquantile(pool, 0.90, axis=0, method='hazen')
    clim[d] = np.nanmean(pool, axis=0)
print("pools computed in %.1f s" % (time.time()-t0))

# sanity: pool sizes expected 121 for all d != 60
assert all(sizes[d]==121 for d in range(1,367) if d!=60), "unexpected pool sizes"
# day 60 = mean of 59 and 61
thr[60]  = 0.5*(thr[59]+thr[61])
clim[60] = 0.5*(clim[59]+clim[61])

def smooth366(a366):  # centred 31-day circular moving mean
    y = np.r_[a366[-15:], a366, a366[:15]]
    return y.reshape(366,31).mean(axis=1)

x = thr[1:]
thr_s  = smooth366(x)
clim_s = smooth366(clim[1:])
# sanity check smoothing with direct mod-index for a few doys
for d in [1, 20, 60, 153, 244, 352, 366]:
    i = d-1
    ref = np.mean(x[(i-15)%366:(i-15)%366+31] if (i-15)%366+31 <= 366 else np.r_[x[(i-15)%366:], x[:((i+16)%366)]])
    print(d, "ok" if np.allclose(ref, thr_s[i]) else "MISMATCH", thr_s[i][1500])
print("threshold smoothed range:", np.nanmin(thr_s), np.nanmax(thr_s))
print("climatology smoothed range:", np.nanmin(clim_s), np.nanmax(clim_s))
print("any NaN thr_s:", np.isnan(thr_s).sum(), "clim_s:", np.isnan(clim_s).sum())
np.save('/tmp/thr_s.npy', thr_s); np.save('/tmp/clim_s.npy', clim_s)
np.save('/tmp/t_doy.npy', t_doy)
print("saved, total %.1f s" % (time.time()-t0))
