import numpy as np, json
mhw = np.load("/tmp/mhw.npy")
Xall = np.load("/tmp/Xall.npy")
X_t = Xall[4028:].reshape(92, 3600)
thr_s = np.load("/tmp/thr_s.npy")
ocean = np.load("/tmp/ocean.npy")
import datetime as dt
from datetime import date
def doy(d): return date(2000,d.month,d.day).toordinal()-date(2000,1,1).toordinal()+1
tdays = [date(2008,6,1)+dt.timedelta(i) for i in range(92)]
tdoy = np.array([doy(d) for d in tdays])
T = thr_s[tdoy-1,:]
hot_o = X_t[:, ocean] >= T[:, ocean]   # (92, nocean)
print("hot_o shape", hot_o.shape)

def brute_cell(h):
    n=len(h); runs=[]; i=0
    while i<n:
        if h[i]:
            j=i
            while j+1<n and h[j+1]: j+=1
            runs.append([i,j]); i=j+1
        else: i+=1
    runs=[r for r in runs if r[1]-r[0]+1>=5]
    changed=True
    while changed:
        changed=False
        for a in range(len(runs)):
            for b in range(a+1,len(runs)):
                if runs[b][0]-runs[a][1]-1 <= 2:
                    runs[a]=[runs[a][0], max(runs[a][1], runs[b][1])]
                    del runs[b]; changed=True; break
            if changed: break
    m=np.zeros(n,bool)
    for s,e in runs: m[s:e+1]=True
    return m

nocean = hot_o.shape[1]
rng = np.random.default_rng(7)
cells = set(int(x) for x in rng.integers(0, nocean, 80))
cells.add(int(np.argmax(hot_o.sum(axis=0))))
mism=0
for ci in sorted(cells):
    if not np.array_equal(brute_cell(hot_o[:,ci]), mhw[:,ocean][:,ci]):
        mism+=1
print("mismatches over", len(cells), "cells:", mism)

perday = mhw.sum(axis=1)
print("events:", json.load(open("/tmp/events.json"))["events"])
print("active day counts:")
for t in range(92):
    if perday[t]>0:
        print(tdays[t].isoformat(), int(perday[t]))
print("n active days:", int((perday>0).sum()))
