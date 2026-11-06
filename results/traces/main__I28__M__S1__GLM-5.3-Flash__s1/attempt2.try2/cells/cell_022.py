script = r'''
import numpy as np, datetime as dt, os, json, time
from collections import defaultdict

work = "/work"
blocks = sorted(os.listdir(work+"/cache"))
parts = [np.load(work+"/cache/"+b, mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
date_index = {d:i for i,d in enumerate(dates)}

ti0 = date_index[dt.date(2013,6,1)]; ti1 = date_index[dt.date(2013,8,31)]
tf = np.isfinite(data32[ti0:ti1+1]).all(axis=0)
data = np.asarray(data32, dtype=np.float64)
del data32, parts
cellT = data.transpose(1,2,0).reshape(3600, data.shape[0])[tf.ravel()]
rows, cols = np.where(tf)
nC = cellT.shape[0]

# ----- pools (interpretation B: +/-5 calendar days around baseline dates of doy d) -----
def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
pools = {}
for d in range(1,367):
    if d == 60: continue
    wins = set()
    for y in range(1992,2003):
        if d == 366 and not isleap(y): continue
        B = dt.date(y,1,1)+dt.timedelta(days=d-1)
        for o in range(-5,6): wins.add(B+dt.timedelta(days=o))
    pools[d] = np.array(sorted((x-start).days for x in wins), np.int64)
print("pool sizes: d1=%d d180=%d d365=%d d366=%d" % (len(pools[1]), len(pools[180]), len(pools[365]), len(pools[366])))

# ----- type-5 / hazen percentile (MATLAB quantile default), NaN-ignoring, vectorized -----
q = 0.90
thr = np.full((366,60,60), np.nan); clim = np.full((366,60,60), np.nan)
t0 = time.time()
for d in range(1,367):
    if d == 60: continue
    V = cellT[:, pools[d]]                      # (nC, n)
    x = np.sort(V, axis=1)
    n = np.isfinite(V).sum(axis=1)
    h = n*q + 0.5                               # 1-based plotting position
    h = np.clip(h, 1.0, n.astype(float))        # clamp beyond last plotting position
    lo = np.floor(h).astype(np.int64); hi = np.ceil(h).astype(np.int64)
    g = h - lo
    xl = np.take_along_axis(x, (lo-1)[:,None], 1)[:,0]
    xh = np.take_along_axis(x, (hi-1)[:,None], 1)[:,0]
    perc = xl + g*(xh - xl)
    perc[n==0] = np.nan
    thr[d-1, rows, cols] = perc
    clim[d-1, rows, cols] = np.nanmean(V, axis=1)
    if d % 120 == 0: print("d", d, "%.1fs" % (time.time()-t0), flush=True)
print("percentiles done %.1fs" % (time.time()-t0))

thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
print("sea finite:", np.isfinite(thr[:,rows,cols]).all(), np.isfinite(clim[:,rows,cols]).all())

def smooth(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return np.stack([ap[d:d+31].mean(axis=0) for d in range(366)])
thr_s = smooth(thr); clim_s = smooth(clim)
np.save(work+"/thr_raw.npy", thr); np.save(work+"/clim_raw.npy", clim)
np.save(work+"/thr_s.npy", thr_s); np.save(work+"/clim_s.npy", clim_s)
np.save(work+"/target_finite.npy", tf)
print("thr_s sea range: %.3f..%.3f" % (np.nanmin(thr_s[:,rows,cols]), np.nanmax(thr_s[:,rows,cols])))

# cross-check vs np.quantile(method="hazen") on 3 doys, all cells
for d in (1, 180, 366):
    V = cellT[:, pools[d]]
    ref = np.quantile(V, 0.9, axis=1, method="hazen")
    md = np.nanmax(np.abs(ref - thr[d-1, rows, cols]))
    print("np.quantile hazen check d=%d: maxdiff %.3e" % (d, md))

# ----- detection -----
sstT = data[ti0:ti1+1]
T = sstT.shape[0]
tdays = dates[ti0:ti1+1]
tdoy = [x.timetuple().tm_yday for x in tdays]
hot = np.greater_equal(sstT, np.stack([thr_s[k-1] for k in tdoy]))
print("hot cells-days:", int(hot.sum()))
print("hot frac Jun %.3f Jul %.3f Aug %.3f" % (hot[:30].mean(), hot[30:61].mean(), hot[61:].mean()))

P = np.zeros((T+2,60,60), np.int8); P[1:-1] = hot
dif = np.diff(P, axis=0)
sr, sy, sx = np.where(dif==1); er, ey, ex = np.where(dif==-1)
sts, ens = defaultdict(list), defaultdict(list)
for r, rc in zip(sr, sy*60+sx): sts[rc].append(r)
for r, rc in zip(er, ey*60+ex): ens[rc].append(r-1)
runs = []
for rc in sts:
    for s, e in zip(sorted(sts[rc]), sorted(ens[rc])):
        if e-s+1 >= 5: runs.append([rc, s, e])
runs.sort(key=lambda z:(z[0],z[1]))
merged = []
for run in runs:
    if merged and merged[-1][0]==run[0] and run[1]-merged[-1][2]-1 <= 2:
        merged[-1][2] = max(merged[-1][2], run[2])
    else: merged.append(run)
lens = np.array([e-s+1 for _,s,e in merged])
print("runs>=5: %d -> per-cell MHWs: %d (len min %d max %d mean %.2f)" % (len(runs), len(merged), lens.min(), lens.max(), lens.mean()))
mhw = np.zeros((T,60,60), np.uint8)
for rc, s, e in merged: mhw[s:e+1, rc//60, rc%60] = 1
print("mhw cells-days:", int(mhw.sum()))
active = mhw.reshape(T,-1).any(axis=1)
ev = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j+1 < T and active[j+1]: j += 1
        ev.append((i,j)); i = j+1
    else: i += 1
events = [{"onset": str(tdays[s]), "end": str(tdays[e])} for s,e in ev]
print("active days:", int(active.sum()), "events:", json.dumps(events))
np.save(work+"/mhw_mask.npy", mhw)
with open(work+"/events.json","w") as f: json.dump(events, f, indent=1)
print("cells with >=1 MHW:", len(set(m[0] for m in merged)), "of", nC)
'''
open("/work/final.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/final.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout); print("STDERR:", r.stderr[-1500:]); print("rc:", r.returncode)
