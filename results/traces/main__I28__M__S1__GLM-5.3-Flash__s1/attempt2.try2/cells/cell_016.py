script = r'''
import numpy as np, datetime as dt, os, json

work = "/work"
blocks = sorted(os.listdir(work+"/cache"))
parts = [np.load(work+"/cache/"+b, mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
date_index = {d:i for i,d in enumerate(dates)}
ti0 = date_index[dt.date(2013,6,1)]; ti1 = date_index[dt.date(2013,8,31)]
tf = np.load(work+"/target_finite.npy")
thr_s = np.load(work+"/thr_s.npy")

sstT = np.asarray(data32[ti0:ti1+1], dtype=np.float64)     # (92,60,60)
T = sstT.shape[0]
tdays = [start + dt.timedelta(days=i) for i in range(ti0, ti1+1)]
tdoy = [d.timetuple().tm_yday for d in tdays]
print("target:", tdays[0], tdays[-1], "doys:", tdoy[0], tdoy[-1], "n:", T)

# hot mask: sst >= threshold for that day-of-year (float64)
thr_for_day = np.stack([thr_s[d-1] for d in tdoy])          # (92,60,60)
hot = np.greater_equal(sstT, thr_for_day)                    # NaN -> False
print("hot days total:", int(hot.sum()), "of", hot.size)
print("hot frac per month: Jun %.3f Jul %.3f Aug %.3f" % tuple(
    hot[:30].mean(), hot[30:61].mean(), hot[61:].mean()))

# ---- per-cell runs >= 5, join gaps <= 2 ----
P = np.zeros((T+2, 60, 60), dtype=bool)
P[1:-1] = hot
dif = np.diff(P.astype(np.int8), axis=0)                     # +1 start, -1 end(exclusive)
start_rows, start_rc = np.where(dif == 1)                    # start row s (0-based target)
end_rows, end_rc = np.where(dif == -1)                       # end row e -> run [s, e-1]
assert len(start_rows) == len(end_rows)
# pair starts with ends per cell: for each cell, starts ascending match ends ascending
from collections import defaultdict
sts, ens = defaultdict(list), defaultdict(list)
for r, (rc) in zip(start_rows, start_rc): sts[rc].append(r)
for r, (rc) in zip(end_rows, end_rc): ens[rc].append(r-1)
runs = []  # (cell, s, e)
for rc in sts:
    ss = sorted(sts[rc]); ee = sorted(ens[rc])
    assert len(ss) == len(ee)
    for s, e in zip(ss, ee):
        assert e >= s
        if e - s + 1 >= 5:
            runs.append([rc, s, e])
print("runs >=5 before join:", len(runs))
# merge per cell (runs already sorted by start per cell since sts ascending)
runs.sort(key=lambda x: (x[0], x[1]))
merged = []
for run in runs:
    if merged and merged[-1][0] == run[0] and run[1] - merged[-1][2] - 1 <= 2:
        merged[-1][2] = max(merged[-1][2], run[2])
    else:
        merged.append(run)
print("per-cell MHWs after join:", len(merged))
lens = np.array([e-s+1 for _,s,e in merged])
print("MHW length: min %d max %d mean %.1f total cells-days %d" % (lens.min(), lens.max(), lens.mean(), lens.sum()))

mhw = np.zeros((T,60,60), np.uint8)
for rc, s, e in merged:
    mhw[s:e+1, rc//60, rc%60] = 1
print("mhw cells-days:", int(mhw.sum()))

# ---- regional events ----
active = mhw.reshape(T,-1).any(axis=1)
print("active days:", int(active.sum()), "of", T)
ev = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j+1 < T and active[j+1]: j += 1
        ev.append((i, j)); i = j+1
    else: i += 1
events = [{"onset": str(tdays[s]), "end": str(tdays[e])} for s,e in ev]
print("regional events:", events)
np.save(work+"/mhw_mask.npy", mhw)
np.save(work+"/active.npy", active)
with open(work+"/events.json","w") as f: json.dump(events, f, indent=1)
# per-cell MHW count per cell for reference
import collections
print("cells with >=1 MHW:", len(set(m[0] for m in merged)), "of sea cells:", int(tf.sum()))
'''
open("/work/detect.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/detect.py"], capture_output=True, text=True, timeout=3600)
print(r.stdout); print("STDERR:", r.stderr[-2000:]); print("rc:", r.returncode)
