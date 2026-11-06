import numpy as np

# 1) hazen p90 == MATLAB default (linear)
x = np.arange(1, 11, dtype=float)
v = np.quantile(x, 0.9, method='hazen')
print("hazen p90 of 1..10:", v, "(expect 9.1 = MATLAB default)")
x2 = np.array([1.0, 2.0, 3.0, 4.0])
print("hazen p90 of 1..4:", np.quantile(x2, 0.9, method='hazen'), "(MATLAB: 3.7)")

# 2) smooth31 wrap-around check
def smooth31(x):
    x3 = np.concatenate([x, x, x], axis=0)
    out = np.full(x.shape, np.nan)
    for d in range(366):
        w = x3[d:d+31]
        out[d] = w.mean(axis=0)
    return out
x = np.arange(366, dtype=float)
# build expected with wrap: for day d, mean of values (d-15..d+15 mod 366)
xw = np.tile(x, 2)
exp_d15 = np.mean([xw[d] for d in range(0, 31)])
got = smooth31(x)
ok = True
for d in [0, 15, 16, 180, 350, 365]:
    vals = [x[(d+k) % 366] for k in range(-15, 16)]
    if not np.isclose(got[d], np.mean(vals)):
        ok = False; print("smooth MISMATCH day", d, got[d], np.mean(vals))
print("smooth31 wrap check:", "PASS" if ok else "FAIL")
# continuity at wrap: mean of 365..0 etc
print("got[0]:", got[0], "manual:", np.mean([x[366-15+i] for i in range(31)]))

# 3) MHW merge logic on synthetic hot vectors
def mhw_of(h):
    """returns list of (start,end) inclusive merged per-cell MHWs"""
    runs = []
    n = len(h); i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]: j += 1
            if j - i >= 5: runs.append((i, j-1))
            i = j
        else:
            i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged

# case a: 5 hot, 1 gap, 5 hot -> one merged 11
h = [True]*5 + [False]*1 + [True]*5 + [False]*3
print("case a:", mhw_of(h), "(expect [(0,10)])")
# case b: 3 hot, gap, 5 hot -> only the 5-run
h = [True]*3 + [False]*2 + [True]*5 + [False]*2
print("case b:", mhw_of(h), "(expect [(5,9)])")
# case c: chain 5,1gap,5,2gap,5 -> one merged
h = [True]*5 + [False]*1 + [True]*5 + [False]*2 + [True]*5
print("case c:", mhw_of(h), "(expect [(0,17)])")
# case d: 3-day gap splits
h = [True]*5 + [False]*3 + [True]*5
print("case d:", mhw_of(h), "(expect [(0,4),(8,12)])")
# case e: 4-day run never qualifies
h = [True]*4 + [False]*1 + [True]*5
print("case e:", mhw_of(h), "(expect [(5,9)])")
# case f: 6 hot with 2 gaps inside? gaps inside a run don't exist by construction; test 5 hot,2 gap,5
h = [True]*5 + [False]*2 + [True]*5
print("case f:", mhw_of(h), "(expect [(0,11)])")

# 4) verify my pipeline's mhw matches a brute-force re-implementation on the real data
import pickle
mhw = np.load('/work/mhw.npy')
with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
SST = np.load('/work/SST_all.npy'); nb = len(dd['base'])
sea_mask = np.load('/work/sea_mask.npy').ravel()
thr_s = np.load('/work/thr_smooth.npy')
from datetime import date
def mdoy(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1
tgt = SST[nb:].reshape(len(dd['tgt']), 3600)
hot = (tgt >= thr_s[np.array([mdoy(d) for d in dd['tgt']]) - 1]) & sea_mask[np.newaxis, :]

mhw2 = np.zeros_like(mhw)
for c in range(3600):
    h = hot[:, c]
    # brute force: label maximal hot runs, keep >=5, merge
    i = 0; n = len(h)
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]: j += 1
            if j - i >= 5:
                mhw2[i:j, c] = 1
            i = j
        else:
            i += 1
# merge pass (independent formulation): iterate until stable
changed = True
while changed:
    changed = False
    for c in range(3600):
        m = mhw2[:, c].copy()
        # find runs of 1s
        i = 0; n = len(m)
        runs = []
        while i < n:
            if m[i]:
                j = i
                while j < n and m[j]: j += 1
                runs.append((i, j-1)); i = j
            else: i += 1
        newruns = []
        for s, e in runs:
            if newruns and s - newruns[-1][1] - 1 <= 2:
                newruns[-1] = (newruns[-1][0], e); changed = True
            else:
                newruns.append((s, e))
        if len(newruns) != len(runs):
            m2 = np.zeros_like(m)
            for s, e in newruns: m2[s:e+1] = 1
            mhw2[:, c] = m2
print("brute-force re-implementation matches pipeline mhw:", np.array_equal(mhw, mhw2))
