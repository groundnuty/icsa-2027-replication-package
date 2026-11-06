script = r'''
import numpy as np, datetime as dt, os, json
from collections import defaultdict

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

sstT = np.asarray(data32[ti0:ti1+1], dtype=np.float64)
T = sstT.shape[0]
tdays = [start + dt.timedelta(days=i) for i in range(ti0, ti1+1)]
tdoy = [d.timetuple().tm_yday for d in tdays]
print("target:", tdays[0], tdays[-1], "doys:", tdoy[0], tdoy[-1], "n:", T)

thr_for_day = np.stack([thr_s[d-1] for d in tdoy])
hot = np.greater_equal(sstT, thr_for_day)
print("hot days total:", int(hot.sum()), "of", hot.size)
print("hot frac per month: Jun %.3f Jul %.3f Aug %.3f" % (hot[:30].mean(), hot[30:61].mean(), hot[61:].mean()))

# runs >= 5, join gaps <= 2
P = np.zeros((T+2, 60, 60), np.int8); P[1:-1] = hot
dif = np.diff(P, axis=0)
sr, src = np.where(dif == 1); er, erc = np.where(dif == -1)
sts, ens = defaultdict(list), defaultdict(list)
for r, rc in zip(sr, src): sts[rc].append(r)
for r, rc in zip(er, erc): ens[rc].append(r-1)
runs = []
for rc in sts:
    for s, e in zip(sorted(sts[rc]), sorted(ens[rc])):
        if e - s + 1 >= 5: runs.append([rc, s, e])
print("runs >=5 before join:", len(runs))
runs.sort(key=lambda x: (x[0], x[1]))
merged = []
for run in runs:
    if merged and merged[-1][0] == run[0] and run[1] - merged[-1][2] - 1 <= 2:
        merged[-1][2] = max(merged[-1][2], run[2])
    else:
        merged.append(run)
print("per-cell MHWs after join:", len(merged))
lens = np.array([e-s+1 for _,s,e in merged])
print("len min %d max %d mean %.1f cells-days %d" % (lens.min(), lens.max(), lens.mean(), lens.sum()))

mhw = np.zeros((T,60,60), np.uint8)
for rc, s, e in merged:
    mhw[s:e+1, rc//60, rc%60] = 1
print("mhw cells-days:", int(mhw.sum()))
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
print("events:", json.dumps(events))
np.save(work+"/mhw_mask.npy", mhw); np.save(work+"/active.npy", active)
with open(work+"/events.json","w") as f: json.dump(events, f, indent=1)
print("cells with >=1 MHW:", len(set(m[0] for m in merged)), "of", int(tf.sum()), "sea cells")
'''
open("/work/detect.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/detect.py"], capture_output=True, text=True, timeout=3600)
print(r.stdout); print("STDERR:", r.stderr[-2000:]); print("rc:", r.returncode)
