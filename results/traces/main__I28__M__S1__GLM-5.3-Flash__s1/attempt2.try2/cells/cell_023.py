script = r'''
import numpy as np, datetime as dt, os, json
from itertools import groupby

work = "/work"
thr_s = np.load(work+"/thr_s.npy"); clim_s = np.load(work+"/clim_s.npy")
tf = np.load(work+"/target_finite.npy")
mhw = np.load(work+"/mhw_mask.npy")
data32 = np.concatenate([np.load(work+"/cache/"+b, mmap_mode="r") for b in sorted(os.listdir(work+"/cache"))], axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
ti0 = dates.index(dt.date(2013,6,1))
sstT = np.asarray(data32[ti0:ti0+92], np.float64)
tdoy = [dates[ti0+k].timetuple().tm_yday for k in range(92)]

def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
pools = {}
for d in range(1,367):
    if d == 60: continue
    wins = set()
    for y in range(1992,2003):
        if d == 366 and not isleap(y): continue
        B = dt.date(y,1,1)+dt.timedelta(days=d-1)
        for o in range(-5,6): wins.add(B+dt.timedelta(days=o))
    pools[d] = sorted(wins)

thr_by_doy, clim_by_doy = {}, {}
for d in pools:
    idx = [(x-start).days for x in pools[d]]
    V = np.asarray(data32[idx], np.float64)
    t = np.full((60,60), np.nan); c = np.full((60,60), np.nan)
    for r in range(60):
        for cc in range(60):
            v = V[:, r, cc]
            if np.isfinite(v).any():
                t[r,cc] = np.quantile(v, 0.9, method="hazen")   # = MATLAB type 5
                c[r,cc] = np.nanmean(v)
    thr_by_doy[d] = t; clim_by_doy[d] = c
thr_by_doy[60] = 0.5*(thr_by_doy[59]+thr_by_doy[61])
clim_by_doy[60] = 0.5*(clim_by_doy[59]+clim_by_doy[61])
def smooth_ind(dic):
    out = {}
    for d in range(1,367):
        s = np.zeros((60,60))
        for j in range(31): s += dic[((d-15+j-1) % 366)+1]
        out[d] = s/31.0
    return out
thrSi = smooth_ind(thr_by_doy); climSi = smooth_ind(clim_by_doy)
print("thr_s brute vs pipeline maxdiff:", max(np.nanmax(np.abs(thrSi[d]-thr_s[d-1])[tf]) for d in range(1,367)))
print("clim_s brute vs pipeline maxdiff:", max(np.nanmax(np.abs(climSi[d]-clim_s[d-1])[tf]) for d in range(1,367)))

hot = np.zeros((92,60,60), bool)
for k in range(92): hot[k] = np.greater_equal(sstT[k], thrSi[tdoy[k]])
print("hot cells-days:", int(hot.sum()), "| Jun:", int(hot[:30].sum()), "Jul:", int(hot[30:61].sum()), "Aug:", int(hot[61:].sum()))
mhw2 = np.zeros((92,60,60), np.uint8); nmhw = 0
for r in range(60):
    for c in range(60):
        seq = [bool(hot[k,r,c]) for k in range(92)]
        runs, pos = [], 0
        for val, grp in groupby(seq):
            L = len(list(grp))
            if val: runs.append([pos, pos+L-1])
            pos += L
        runs = [x for x in runs if x[1]-x[0]+1 >= 5]
        merged = []
        for x in runs:
            if merged and x[0]-merged[-1][1]-1 <= 2: merged[-1][1] = x[1]
            else: merged.append(x)
        nmhw += len(merged)
        for s,e in merged: mhw2[s:e+1, r, c] = 1
print("brute per-cell MHWs:", nmhw, "| mask identical:", np.array_equal(mhw, mhw2))
active = mhw2.reshape(92,-1).any(axis=1)
ev, k = [], 0
while k < 92:
    if active[k]:
        j = k
        while j+1 < 92 and active[j+1]: j += 1
        ev.append((str(start+dt.timedelta(days=ti0+k)), str(start+dt.timedelta(days=ti0+j)))); k = j+1
    else: k += 1
print("events:", ev)
print("saved events:", json.load(open(work+"/events.json")))
# regional-mean anomaly by month for context
anom = sstT - np.stack([climSi[d-1] for d in tdoy])
for nm, sl in [("Jun",slice(0,30)),("Jul",slice(30,61)),("Aug",slice(61,92))]:
    print(nm, "region-mean anomaly %+.2f K" % np.nanmean(anom[sl][:, tf]))
'''
open("/work/validate2.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/validate2.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout); print("STDERR:", r.stderr[-1500:]); print("rc:", r.returncode)
