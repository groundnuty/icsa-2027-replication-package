import numpy as np, datetime as dt, json
from datetime import date
mhw = np.load("/tmp/mhw.npy"); hot = None
Xall = np.load("/tmp/Xall.npy")
X_t = Xall[4028:].reshape(92, 3600)
thr_s = np.load("/tmp/thr_s.npy")
ocean = np.load("/tmp/ocean.npy")
def doy(d): return date(2000,d.month,d.day).toordinal()-date(2000,1,1).toordinal()+1
tdays = [date(2008,6,1)+dt.timedelta(i) for i in range(92)]
tdoy = np.array([doy(d) for d in tdays])
T = thr_s[tdoy-1,:]
hot = (X_t[:, ocean] >= T[:, ocean])  # (92, nocean)

def brute_cell(h):
    """independent: explicit scan + transitive gap join"""
    n=len(h)
    # initial runs
    runs=[]; i=0
    while i<n:
        if h[i]:
            j=i
            while j+1<n and h[j+1]: j+=1
            runs.append([i,j]); i=j+1
        else: i+=1
    runs=[r for r in runs if r[1]-r[0]+1>=5]
    merged=True
    while merged:
        merged=False
        for a in range(len(runs)):
            for b in range(a+1,len(runs)):
                if runs[b][0]-runs[a][1]-1<=2:
                    runs[a]=[runs[a][0], max(runs[a][1], runs[b][1])]
                    del runs[b]; merged=True; break
            if merged: break
    m=np.zeros(n,bool)
    for s,e in runs: m[s:e+1]=True
    return m

nocean = int(ocean.sum())
rng=np.random.default_rng(7)
cells = list(rng.integers(0, nocean, 60)) + [np.argmax(hot.sum(axis=0))]  # add busiest
mism=0
for ci in cells:
    ref = brute_cell(hot[:,ci])
    if not np.array_equal(ref, mhw[:, ocean][ci]): mism+=1; print("MISMATCH cell", ci)
print("mismatches over", len(cells), "cells:", mism)

perday = mhw.sum(axis=1)
ev = json.load(open("/tmp/events.json"))
print("events:", ev["events"])
print("per-day cell counts (active days only):")
for t in range(92):
    if perday[t]>0: print(tdays[t].isoformat(), int(perday[t]))
print("days with >0:", int((perday>0).sum()), "| gap check within event: min count in 06-02..06-10 =", int(perday[1:10].min()))
