script = r'''
import numpy as np, datetime as dt, os, json, time

work = "/work"
blocks = sorted(os.listdir(os.path.join(work, "cache")))
parts = [np.load(os.path.join(work, "cache", b), mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
ndays = data32.shape[0]
dates = [start + dt.timedelta(days=i) for i in range(ndays)]
date_index = {d: i for i, d in enumerate(dates)}

t0, t1 = dt.date(2013,6,1), dt.date(2013,8,31)
ti0, ti1 = date_index[t0], date_index[t1]
target_finite = np.isfinite(data32[ti0:ti1+1]).all(axis=0)
print("sea cells:", int(target_finite.sum()))

data = np.asarray(data32, dtype=np.float64)
del data32, parts

b_lo, b_hi = dt.date(1992,1,1), dt.date(2002,12,31)
cand = [i for i, d in enumerate(dates)
        if b_lo <= d <= b_hi or d <= dt.date(1991,12,31) or (dt.date(2003,1,1) <= d <= dt.date(2003,1,5))]
print("candidate test days:", len(cand), dates[cand[0]], dates[cand[-1]])

def in_pool(test, d):   # d in 1..366, d != 60
    td = test.timetuple().tm_yday
    return -5 <= td - d <= 5

pools = {}
for d in range(1, 367):
    if d == 60: continue
    pools[d] = np.array([i for i in cand if in_pool(dates[i], d)], dtype=np.int64)
sizes = np.array([len(pools[d]) for d in pools])
print("pool sizes: min %d max %d mean %.2f" % (sizes.min(), sizes.max(), sizes.mean()))
print("d=1: %d  d=180: %d  d=365: %d  d=366: %d" % (len(pools[1]), len(pools[180]), len(pools[365]), len(pools[366])))

# vectorized hazen percentile per column (NaN sorted to end)
q = 0.90
cells = np.where(target_finite)
thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
t0 = time.time()
for d in range(1, 367):
    if d == 60: continue
    idx = pools[d]
    V = data[np.ix_(idx, cells[0], cells[1])]        # (n_pool, n_cells)
    x = np.sort(V, axis=0)                           # NaN last
    n = np.isfinite(V).sum(axis=0)                   # (n_cells,)
    with np.errstate(invalid="ignore"):
        h = (n - 1) * q + 1.0
        lo = np.floor(h).astype(int); hi = np.ceil(h).astype(int)
        g = h - lo
        xl = np.take_along_axis(x, np.clip(lo-1, 0, x.shape[0]-1)[None, :], axis=0)[0]
        xh = np.take_along_axis(x, np.clip(hi-1, 0, x.shape[0]-1)[None, :], axis=0)[0]
        perc = xl + g * (xh - xl)
        perc[n == 0] = np.nan
        perc[n == 1] = x[0][n == 1]
        thr[d-1, cells[0], cells[1]] = perc
        clim[d-1, cells[0], cells[1]] = np.nanmean(V, axis=0)
print("percentile loop done %.1fs" % (time.time()-t0))

# day 60 <- mean(day 59, day 61)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("sea-cell thr finite:", np.isfinite(thr[:, cells[0], cells[1]]).all(),
      "clim finite:", np.isfinite(clim[:, cells[0], cells[1]]).all())
print("land cells all-NaN (expected):", np.isnan(thr[:, ~target_finite]).all())

def circ_movmean31(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    out = np.empty_like(a)
    for d in range(366):
        out[d] = ap[d:d+31].mean(axis=0)
    return out

thr_s = circ_movmean31(thr)
clim_s = circ_movmean31(clim)
np.save(os.path.join(work, "thr_raw.npy"), thr)
np.save(os.path.join(work, "clim_raw.npy"), clim)
np.save(os.path.join(work, "thr_s.npy"), thr_s)
np.save(os.path.join(work, "clim_s.npy"), clim_s)
np.save(os.path.join(work, "target_finite.npy"), target_finite)
print("saved. thr_s range over sea cells: %.3f .. %.3f" % (np.nanmin(thr_s[:, cells[0], cells[1]]), np.nanmax(thr_s[:, cells[0], cells[1]])))
# sanity: smoothed must equal raw mean of neighbours for an interior day
d0 = 200
manual = np.mean([thr[(d0-15+j) % 366] for j in range(31)], axis=0)
print("smooth check day200 max abs diff:", np.abs(manual - thr_s[d0-1]).max())
'''
with open("analysis2.py", "w") as f:
    f.write(script)
import subprocess
r = subprocess.run(["python", "analysis2.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout)
print("STDERR:", r.stderr[-1500:])
print("rc:", r.returncode)
