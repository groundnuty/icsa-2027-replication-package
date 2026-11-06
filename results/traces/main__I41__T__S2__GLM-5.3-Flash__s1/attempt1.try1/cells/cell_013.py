import numpy as np, datetime as dt, time, pickle, warnings
B = np.load('work/B.npy')   # (4028, 60, 60) float32, row 0 = 1991-12-27
with open('work/pools.pkl','rb') as f_:
    pool_by_doy = pickle.load(f_)

B64 = B.astype(np.float64)
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)

t0 = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    rows = pool_by_doy[d]
    pool = B64[rows]   # (121, 60, 60)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        thr_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(pool, axis=0)
print("recompute time: %.1f s" % (time.time()-t0))

# day 60 = mean of days 59 and 61
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print("thr_raw finite frac:", np.isfinite(thr_raw).mean(), "| clim finite frac:", np.isfinite(clim_raw).mean())

# sanity: compare with old (wrong-mask) values at a mid-year doy to see they differ
old_thr = np.load('work/thr_raw.npy')
print("doy153 mean |new-old| thr:", np.nanmean(np.abs(thr_raw[152]-old_thr[152])), "(nonzero expected)")
print("doy153 mean |new-old| where equal doy? doy366:", np.nanmean(np.abs(thr_raw[365]-old_thr[365])))

np.save('work/thr_raw.npy', thr_raw); np.save('work/clim_raw.npy', clim_raw)
print("saved raw (correct) arrays.")
# quick look at a sample cell's threshold in target season
cell = (30, 30)
for d in [153, 180, 210, 244]:
    print("doy", d, "thr:", round(thr_raw[d-1][cell],3), "clim:", round(clim_raw[d-1][cell],3))
