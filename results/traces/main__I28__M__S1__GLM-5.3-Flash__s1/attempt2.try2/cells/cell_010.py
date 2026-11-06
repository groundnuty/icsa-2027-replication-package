script = r'''
import numpy as np, datetime as dt, os, json, time

work = "/work"
# ---------- 1. load cached data ----------
blocks = sorted(os.listdir(os.path.join(work, "cache")))
parts = [np.load(os.path.join(work, "cache", b), mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)          # (7919,60,60) float32
start = dt.date(1991,12,27)
ndays = data32.shape[0]
dates = [start + dt.timedelta(days=i) for i in range(ndays)]
date_index = {d: i for i, d in enumerate(dates)}
print("loaded", data32.shape, dates[0], dates[-1])

# ---------- 2. region & sea cells ----------
t0, t1 = dt.date(2013,6,1), dt.date(2013,8,31)
ti0, ti1 = date_index[t0], date_index[t1]
print("target idx:", ti0, ti1, "n:", ti1-ti0+1)
target_finite = np.isfinite(data32[ti0:ti1+1]).all(axis=0)     # (60,60) bool
print("sea cells:", int(target_finite.sum()), "of", target_finite.size)

data = np.asarray(data32, dtype=np.float64)     # float64 copy, ~229 MB
del data32, parts

# ---------- 3. baseline indices & pools ----------
b_lo, b_hi = dt.date(1992,1,1), dt.date(2002,12,31)
bi = [i for i, d in enumerate(dates) if b_lo <= d <= b_hi]
print("baseline days:", len(bi), dates[bi[0]], dates[bi[-1]])
# extended pool days: 1991-12-27..31 (already included: start=1991-12-27) and 2003-01-01..05
ext_after = [date_index[dt.date(2003,1,k)] for k in range(1,6)]
print("ext after:", [str(dates[i]) for i in ext_after], "| ext before:", [str(dates[0])])

def doy_of(d):
    return (d.timetuple().tm_yday)

def testdate_in_window(test, d):  # d = day-of-year 1..366
    td = test.timetuple().tm_yday
    ty, isleap = test.year, (test.timetuple().tm_yday == 366)
    for k in range(6):            # offsets 0..+5
        yy = test.year if d >= td else (test.year + 1)
        v = dt.date(yy,1,1) + dt.timedelta(days=d-1)
        if v == test + dt.timedelta(days=k) and v.timetuple().tm_yday == d and v.month == ((d<=59)*1+3) if False else True:
            pass
    return False

# simpler, explicit: a test date is in d's pool iff its doy (Feb29->60) equals
# d+offset for some offset in 0..5 (mod-366 not needed: windows never cross Dec31,
# they are defined by calendar neighbours).
def in_pool(test, d):
    td = doy_of(test)
    return any(td == d + k for k in range(6))

pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    idx = [i for i in bi if in_pool(dates[i], d)] + (ext_after if in_pool(dt.date(2003,1,5), d) and False else [])
    pools[d] = idx
# attach 2003-01-01..05 to their windows via in_pool (they are simply test dates):
for i in ext_after:
    td = doy_of(dates[i])
    for d in range(max(1, td-5), min(366, td)+1):
        pass
# The in_pool function above already handles extension dates if we include them as
# candidate tests. Redo cleanly:
def build_pool(d):
    cand = [i for i in bi if in_pool(dates[i], d)]
    for i in ext_after:                      # 2003-01-01..05
        if in_pool(dates[i], d):
            cand.append(i)
    return np.array(sorted(cand), dtype=np.int64)

pools = {d: build_pool(d) for d in range(1, 367) if d != 60}
sizes = np.array([len(pools[d]) for d in range(1,367) if d != 60])
print("pool sizes: min %d max %d mean %.1f" % (sizes.min(), sizes.max(), sizes.mean()))
print("pool d=180:", len(pools[180]), "d=1:", len(pools[1]), "d=365:", len(pools[365]), "d=366:", len(pools[366]))

# ---------- 4. percentile (hazen) & mean per cell ----------
def hazen_percentile(a, q):
    """MATLAB quantile default = Hyndman-Fan type 5, ignoring NaN."""
    x = a[np.isfinite(a)]
    n = x.size
    if n == 0:
        return np.nan
    if n == 1:
        return float(x[0])
    h = (n - 1) * q + 1          # 1-based index
    lo = int(np.floor(h))
    hi = int(np.ceil(h))
    if lo == hi:
        return float(x[lo-1])
    g = h - lo
    return float(x[lo-1] + g * (x[hi-1] - x[lo-1]))

thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
q = 0.90
t0 = time.time()
for c in range(60):
    for r in range(60):
        if not target_finite[r, c]:
            continue
        col = data[:, r, c]
        for d in range(1, 367):
            if d == 60:
                continue
            vals = col[pools[d]]
            thr[d-1, r, c] = hazen_percentile(vals, q)
            clim[d-1, r, c] = np.nanmean(vals)
    if c % 10 == 0:
        print("col %d done %.1fs" % (c, time.time()-t0), flush=True)
print("percentiles done %.1fs" % (time.time()-t0))

# day 60 <- mean of day 59 and 61 (both thr and clim)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
assert np.isfinite(thr).all() and np.isfinite(clim).all()

# ---------- 5. 31-day circular moving mean ----------
def circ_movmean31(a):   # a: (366, ...)
    k = np.ones(31)/31.0
    out = np.full_like(a, np.nan)
    for d0 in range(366):
        idx = [(d0-15+j) % 366 for j in range(31)]
        out[d0] = a[idx].mean(axis=0)
    return out

thr_s = circ_movmean31(thr)
clim_s = circ_movmean31(clim)
np.save(os.path.join(work, "thr_s.npy"), thr_s)
np.save(os.path.join(work, "clim_s.npy"), clim_s)
np.save(os.path.join(work, "target_finite.npy"), target_finite)
print("smoothing done; sample thr d180 c0r0: %.4f  raw: %.4f" % (thr_s[179,0,0], thr[179,0,0]))
print("sea cell thr range: %.3f..%.3f" % (np.nanmin(thr_s[:, target_finite]), np.nanmax(thr_s[:, target_finite])))
'''
with open("analysis.py", "w") as f:
    f.write(script)
print("script written")
import subprocess
r = subprocess.run(["python", "analysis.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout[-4000:])
print("STDERR:", r.stderr[-3000:])
print("rc:", r.returncode)
