script = r'''
import numpy as np, datetime as dt, os, json
from itertools import groupby

work = "/work"
thr_s = np.load(work+"/thr_s.npy"); clim_s = np.load(work+"/clim_s.npy")
mhw = np.load(work+"/mhw_mask.npy"); tf = np.load(work+"/target_finite.npy")

# ---------- anomaly context ----------
blocks = sorted(os.listdir(work+"/cache"))
parts = [np.load(work+"/cache/"+b, mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
ti0 = dates.index(dt.date(2013,6,1))
sstT = np.asarray(data32[ti0:ti0+92], dtype=np.float64)
tdoy = [dates[ti0+k].timetuple().tm_yday for k in range(92)]
anom = sstT - np.stack([clim_s[d-1] for d in tdoy])
for name, sl in [("Jun", slice(0,30)), ("Jul", slice(30,61)), ("Aug", slice(61,92))]:
    a = anom[sl][:, tf]
    print("%s anomaly mean %+.2f K, min %+.2f, max %+.2f" % (name, np.nanmean(a), np.nanmin(a), np.nanmax(a)))
print("Anomaly > 0.9*pct-noise only in June -> consistent with no August events.")
del data32, parts

# ---------- independent brute force recompute of the whole mask ----------
data32 = np.concatenate([np.load(work+"/cache/"+b, mmap_mode="r") for b in blocks], axis=0)
def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
base_dates = [dt.date(y,1,1)+dt.timedelta(days=i) for y in range(1992,2003) for i in range(366 if isleap(y) else 365)]
base_set = set(base_dates)
pools = {}
for d in range(1,367):
    if d == 60: continue
    wins = set()
    for y in range(1992,2003):
        if d == 366 and not isleap(y): continue
        B = dt.date(y,1,1)+dt.timedelta(days=d-1)
        for o in range(-5,6): wins.add(B+dt.timedelta(days=o))
    pools[d] = sorted(wins)
# verify pools only contain days we have in cache and are within 1991-12-27..2003-01-05
print("pool day-range check:", min(min(v) for v in pools.values()), max(max(v) for v in pools.values()))

def hazen(v):
    x = np.sort(v[np.isfinite(v)]); n = x.size
    if n == 0: return np.nan
    if n == 1: return float(x[0])
    h = (n-1)*0.9+1; lo, hi = int(np.floor(h)), int(np.ceil(h))
    return float(x[lo-1]+(h-lo)*(x[hi-1]-x[lo-1]))

thr_by_doy = {}   # doy -> (60,60)
clim_by_doy = {}
for d in pools:
    idx = [ (x - start).days for x in pools[d] ]
    V = np.asarray(data32[idx], dtype=np.float64)            # (n,60,60)
    t = np.full((60,60), np.nan); c = np.full((60,60), np.nan)
    for r in range(60):
        for cc in range(60):
            v = V[:, r, cc]
            if np.isfinite(v).any():
                t[r,cc] = hazen(v); c[r,cc] = np.nanmean(v)
    thr_by_doy[d] = t; clim_by_doy[d] = c
thr_by_doy[60] = 0.5*(thr_by_doy[59]+thr_by_doy[61])
clim_by_doy[60] = 0.5*(clim_by_doy[59]+clim_by_doy[61])

# independent smoothing: explicit modulo accumulation
def smooth_ind(dic):
    out = {}
    for d in range(1,367):
        s = np.zeros((60,60))
        for j in range(31):
            s += dic[((d-15+j-1) % 366)+1]
        out[d] = s/31.0
    return out
thrSi = smooth_ind(thr_by_doy); climSi = smooth_ind(clim_by_doy)

maxdiff = max(np.nanmax(np.abs(thrSi[d]-thr_s[d-1])[tf]) for d in range(1,367))
print("smoothed threshold brute-force vs pipeline maxdiff (sea):", maxdiff)
maxdiff2 = max(np.nanmax(np.abs(climSi[d]-clim_s[d-1])[tf]) for d in range(1,367))
print("smoothed climatology maxdiff (sea):", maxdiff2)

# hot + runs via groupby (independent)
hot = np.zeros((92,60,60), bool)
for k in range(92):
    hot[k] = np.greater_equal(sstT[k], thrSi[tdoy[k]])
mhw2 = np.zeros((92,60,60), np.uint8)
nruns = 0; nmhw = 0
for r in range(60):
    for c in range(60):
        seq = [bool(hot[k,r,c]) for k in range(92)]
        # run-length encode
        runs = []
        pos = 0
        for val, grp in groupby(seq):
            L = len(list(grp))
            if val: runs.append([pos, pos+L-1])
            pos += L
        runs = [x for x in runs if x[1]-x[0]+1 >= 5]
        nruns += len(runs)
        merged = []
        for x in runs:
            if merged and x[0]-merged[-1][1]-1 <= 2:
                merged[-1][1] = x[1]
            else: merged.append(x)
        nmhw += len(merged)
        for s,e in merged:
            mhw2[s:e+1, r, c] = 1
print("brute-force runs>=5:", nruns, "MHWs:", nmhw)
same = np.array_equal(mhw, mhw2)
print("MASK IDENTICAL to pipeline:", same)
if not same:
    d = np.argwhere(mhw != mhw2); print("diffs:", d[:20], len(d))

# regional events brute force
active = mhw2.reshape(92,-1).any(axis=1)
ev = []
k = 0
while k < 92:
    if active[k]:
        j = k
        while j+1 < 92 and active[j+1]: j += 1
        ev.append((start+dt.timedelta(days=ti0+k), start+dt.timedelta(days=ti0+j))); k = j+1
    else: k += 1
print("events (brute force):", [(str(a), str(b)) for a,b in ev])
print("saved events:", json.load(open(work+"/events.json")))
'''
open("/work/validate.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/validate.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout); print("STDERR:", r.stderr[-2000:]); print("rc:", r.returncode)
