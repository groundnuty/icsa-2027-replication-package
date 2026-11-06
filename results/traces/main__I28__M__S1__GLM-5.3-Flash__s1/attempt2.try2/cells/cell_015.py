script = r'''
import numpy as np, datetime as dt, os, time

work = "/work"
blocks = sorted(os.listdir(work+"/cache"))
parts = [np.load(work+"/cache/"+b, mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
date_index = {d: i for i, d in enumerate(dates)}

ti0 = date_index[dt.date(2013,6,1)]; ti1 = date_index[dt.date(2013,8,31)]
tf = np.isfinite(data32[ti0:ti1+1]).all(axis=0)
data = np.asarray(data32, dtype=np.float64)
del data32, parts
cellT = data.transpose(1,2,0).reshape(3600, data.shape[0])[tf.ravel()]
rows, cols = np.where(tf)

def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
def cal_date(y, doy): return dt.date(y,1,1) + dt.timedelta(days=doy-1)

# Interpretation (B): pool(d) = dates within +/-5 CALENDAR days of any baseline
# date (1992-01-01..2002-12-31) whose day-of-year is d. 29 Feb -> doy 60.
poolsB = {}
for d in range(1, 367):
    if d == 60: continue
    s = set()
    for y in range(1992, 2003):
        if d == 366 and not isleap(y): continue
        B = cal_date(y, d)
        for o in range(-5, 6):
            t = B + dt.timedelta(days=o)
            j = date_index.get(t)
            if j is not None: s.add(j)
    poolsB[d] = np.array(sorted(s), np.int64)
sizesB = {d: len(poolsB[d]) for d in poolsB}
print("B pools: d1=%d d5=%d d6=%d d180=%d d361=%d d365=%d d366=%d" %
      (sizesB[1], sizesB[5], sizesB[6], sizesB[180], sizesB[361], sizesB[365], sizesB[366]))
uniq = set(sizesB.values()); print("B distinct pool sizes:", sorted(uniq))

# Interpretation (A) for comparison: doy-distance with extension days as test dates
cand = np.array([i for i,d in enumerate(dates)
     if (dt.date(1992,1,1) <= d <= dt.date(2002,12,31)) or d <= dt.date(1991,12,31)
     or (dt.date(2003,1,1) <= d <= dt.date(2003,1,5))], np.int64)
poolsA = {d: np.array([i for i in cand if -5 <= dates[i].timetuple().tm_yday - d <= 5], np.int64)
          for d in range(1,367) if d != 60}

q = 0.90
def compute(pools):
    thr = np.full((366,60,60), np.nan); clim = np.full((366,60,60), np.nan)
    for d in range(1, 367):
        if d == 60: continue
        V = cellT[:, pools[d]]
        x = np.sort(V, axis=1); n = np.isfinite(V).sum(axis=1)
        with np.errstate(invalid="ignore"):
            h = (n-1)*q + 1.0
            lo = np.floor(h).astype(np.int64); hi = np.ceil(h).astype(np.int64)
            g = h - lo
            xl = np.take_along_axis(x, np.clip(lo-1,0,x.shape[1]-1)[:,None],1)[:,0]
            xh = np.take_along_axis(x, np.clip(hi-1,0,x.shape[1]-1)[:,None],1)[:,0]
            perc = xl + g*(xh-xl); perc[n==0] = np.nan
            m1 = n==1
            if m1.any(): perc[m1] = x[:,0][m1]
            thr[d-1, rows, cols] = perc
            clim[d-1, rows, cols] = np.nanmean(V, axis=1)
    thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
    return thr, clim

def smooth(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return np.stack([ap[d:d+31].mean(axis=0) for d in range(366)])

t0=time.time()
thrB, climB = compute(poolsB)
thrBs, climBs = smooth(thrB), smooth(climB)
thrA, climA = compute(poolsA)
thrAs, climAs = smooth(thrA), smooth(climA)
print("computed %.1fs" % (time.time()-t0))

# compare target-period smoothed values (doys 153..243), where results must agree
sl = slice(152, 243)
dB = np.nanmax(np.abs(thrBs[sl] - thrAs[sl])[:, rows, cols])
print("max |thr_s B - A| over target doys (sea cells):", dB)
# check interior raw equality
intr = [d for d in range(1,367) if d not in (60,)]
diff_int = max(np.nanmax(np.abs(thrB[d-1]-thrA[d-1])[rows,cols]) for d in range(140,260))
print("max |raw B - A| doys 140-259:", diff_int)
# NaN count in baseline pools for sea cells (missing baseline data?)
nn = np.mean([np.mean(~np.isfinite(cellT[:, poolsB[d]])) for d in range(1,367) if d!=60])
print("mean fraction NaN in pools:", nn)

np.save(work+"/thr_raw.npy", thrB); np.save(work+"/clim_raw.npy", climB)
np.save(work+"/thr_s.npy", thrBs); np.save(work+"/clim_s.npy", climBs)
np.save(work+"/target_finite.npy", tf)
# smoothing self-check, correctly indexed (0-based)
d0 = 199
manual = np.mean([thrB[(d0-15+j) % 366] for j in range(31)], axis=0)
print("smooth self-check (0-based d0=199) maxdiff sea:", np.nanmax(np.abs(manual-thrBs[d0])[rows,cols]))
print("thr_s sea range: %.3f..%.3f" % (np.nanmin(thrBs[:,rows,cols]), np.nanmax(thrBs[:,rows,cols])))
'''
open("/work/analysis5.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/analysis5.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout); print("STDERR:", r.stderr[-1500:]); print("rc:", r.returncode)
