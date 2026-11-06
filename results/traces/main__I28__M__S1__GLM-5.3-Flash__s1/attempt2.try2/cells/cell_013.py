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

# cell-major matrix: (n_cells, n_days) for sea cells
cellT = data.transpose(1, 2, 0).reshape(3600, data.shape[0])[target_finite.ravel()]
print("cellT:", cellT.shape, cellT.dtype)

cand = np.array([i for i, d in enumerate(dates)
        if (dt.date(1992,1,1) <= d <= dt.date(2002,12,31)) or d <= dt.date(1991,12,31)
        or (dt.date(2003,1,1) <= d <= dt.date(2003,1,5))], dtype=np.int64)

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
    V = cellT[:, pools[d]]            # (3301, n_pool)
    x = np.sort(V, axis=1)
    n = np.isfinite(V).sum(axis=1)
    with np.errstate(invalid="ignore"):
        h = (n - 1) * q + 1.0
        lo = np.floor(h).astype(np.int64); hi = np.ceil(h).astype(np.int64)
        g = (h - lo)[:, None]
        ll = np.clip(lo-1, 0, x.shape[1]-1)[:, None]
        hh = np.clip(hi-1, 0, x.shape[1]-1)[:, None]
        xl = np.take_along_axis(x, ll, axis=1)[:, 0]
        xh = np.take_along_axis(x, hh, axis=1)[:, 0]
        perc = xl + g[:, 0] * (xh - xl)
        perc[n == 0] = np.nan
        m1 = n == 1
        if m1.any(): perc[m1] = x[:, 0][m1]
        thr[d-1, rows, cols] = perc
        clim[d-1, rows, cols] = np.nanmean(V, axis=1)
    if d % 120 == 0: print("d", d, "%.1fs" % (time.time()-t0), flush=True)
print("percentiles done %.1fs" % (time.time()-t0))

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
# hazen vs alternative methods sanity at one cell/doy
V = cellT[:, pools[180]]
import numpy.linalg as la
print("n pool 180:", V.shape[1], "finite:", np.isfinite(V[:,0]).sum())
'''
open("/work/analysis4.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/analysis4.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout); print("STDERR:", r.stderr[-1200:]); print("rc:", r.returncode)
