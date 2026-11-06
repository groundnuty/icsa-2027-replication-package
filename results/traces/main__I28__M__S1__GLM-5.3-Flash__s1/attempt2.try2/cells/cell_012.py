script = r'''
import numpy as np, datetime as dt, os, time

work = "/work"
blocks = sorted(os.listdir(os.path.join(work, "cache")))
parts = [np.load(os.path.join(work, "cache", b), mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]

ti0 = dates.index(dt.date(2013,6,1)); ti1 = dates.index(dt.date(2013,8,31))
target_finite = np.isfinite(data32[ti0:ti1+1]).all(axis=0)
data = np.asarray(data32, dtype=np.float64)
del data32, parts

cand = [i for i, d in enumerate(dates)
        if (dt.date(1992,1,1) <= d <= dt.date(2002,12,31)) or d <= dt.date(1991,12,31)
        or (dt.date(2003,1,1) <= d <= dt.date(2003,1,5))]

def in_pool(test, d):
    return -5 <= test.timetuple().tm_yday - d <= 5

pools = {d: np.array([i for i in cand if in_pool(dates[i], d)], np.int64)
         for d in range(1, 367) if d != 60}

rows, cols = np.where(target_finite)
q = 0.90
thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
t0 = time.time()
for d in range(1, 367):
    if d == 60: continue
    idx = pools[d]
    V = data[idx][:, rows, cols]          # (n_pool, 3301)
    x = np.sort(V, axis=0)
    n = np.isfinite(V).sum(axis=0)
    with np.errstate(invalid="ignore"):
        h = (n - 1) * q + 1.0
        lo = np.floor(h).astype(int); hi = np.ceil(h).astype(int)
        g = h - lo
        ll = np.clip(lo-1, 0, x.shape[0]-1); hh = np.clip(hi-1, 0, x.shape[0]-1)
        xl = x[ll]; xh = x[hh]
        perc = xl + g * (xh - xl)
        perc[n == 0] = np.nan
        perc[n == 1] = x[0][n == 1]
        thr[d-1, rows, cols] = perc
        clim[d-1, rows, cols] = np.nanmean(V, axis=0)
print("percentiles %.1fs" % (time.time()-t0))

thr[59] = 0.5*(thr[58] + thr[60]); clim[59] = 0.5*(clim[58] + clim[60])
print("sea-cell finite:", np.isfinite(thr[:, rows, cols]).all(), np.isfinite(clim[:, rows, cols]).all())

def circ_movmean31(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return np.stack([ap[d:d+31].mean(axis=0) for d in range(366)])

thr_s = circ_movmean31(thr); clim_s = circ_movmean31(clim)
np.save(work+"/thr_raw.npy", thr); np.save(work+"/clim_raw.npy", clim)
np.save(work+"/thr_s.npy", thr_s); np.save(work+"/clim_s.npy", clim_s)
np.save(work+"/target_finite.npy", target_finite)
print("saved; thr_s sea range %.3f..%.3f" % (np.nanmin(thr_s[:, rows, cols]), np.nanmax(thr_s[:, rows, cols])))
d0 = 200
manual = np.mean([thr[(d0-15+j) % 366] for j in range(31)], axis=0)
print("smooth check day200 maxdiff:", np.abs(manual - thr_s[d0-1]).max())
'''
open("/work/analysis3.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/analysis3.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout); print("STDERR:", r.stderr[-1200:]); print("rc:", r.returncode)
