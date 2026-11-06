import numpy as np
mhw = np.load('/work/mhw.npy'); sea = np.load('/work/sea.npy')
thr = np.load('/work/thr.npy'); target_arr = np.load('/work/target_arr.npy'); doy_target = np.load('/work/doy_target.npy')
hot = (target_arr.T >= thr[:, doy_target]) & np.isfinite(target_arr.T) & sea[:, None]
Tt = hot.shape[1]

def cell_mhw_bruteforce(h):
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]:
                j += 1
            runs.append((i, j)); i = j+1
        else:
            i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    # merge transitively
    i = 0
    while i < len(runs)-1:
        g = runs[i+1][0] - runs[i][1] - 1
        if g <= 2:
            runs[i] = (runs[i][0], runs[i+1][1])
            del runs[i+1]
        else:
            i += 1
    out = np.zeros(n, dtype=bool)
    for s, e in runs:
        out[s:e+1] = True
    return out

bad = 0
for c in range(3600):
    ref = cell_mhw_bruteforce(hot[c])
    if not np.array_equal(ref.view(np.uint8), mhw[c]):
        bad += 1
        if bad <= 3:
            print("MISMATCH cell", c)
print("cells mismatched:", bad, "of", 3600)

# also verify no MHW spans across a gap of >=3 by construction (brute force guarantees), and event consistency
active = mhw.any(axis=0)
import datetime as dt
dates = [dt.date(2009,6,1)+dt.timedelta(days=i) for i in range(Tt)]
# recompute events independently
ev = []
runs = []
i = 0
while i < Tt:
    if active[i]:
        j = i
        while j+1 < Tt and active[j+1]: j += 1
        ev.append((dates[i], dates[j])); i = j+1
    else:
        i += 1
print("events:", ev)
