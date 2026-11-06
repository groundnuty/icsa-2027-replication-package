import numpy as np
from datetime import date

block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")
thr = np.load("/tmp/thr_smooth.npy")
nb = 4028
target_days = alldays[nb:]; nt = len(target_days)
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of(s):
    m, d = int(s[5:7]), int(s[8:10]); return cum_before[m-1] + d

sst = block[nb:].astype(np.float64)
tdoy = np.array([doy_of(s) for s in target_days])
hot = sst >= thr[tdoy - 1]
hot[:, ~sea_cells] = False

# hot-run structure per cell: all runs (any length)
flat = hot.reshape(nt, -1)
from collections import Counter
runlen = Counter()
amb_cases = []   # pairs of >=5d runs separated only by a short hot run with <=2 non-hot each side
for c in range(flat.shape[1]):
    seq = flat[:, c]
    if not seq.any(): continue
    idx = np.flatnonzero(np.diff(np.concatenate(([False], seq, [False])).astype(np.int8)))
    starts = idx[0::2]; ends = idx[1::2]-1
    runs = list(zip(starts, ends))
    for s, e in runs: runlen[e-s+1] += 1
    big = [(s,e) for s,e in runs if e-s+1 >= 5]
    for i in range(len(big)-1):
        s1, e1 = big[i]; s2, e2 = big[i+1]
        gap = list(range(e1+1, s2))
        if len(gap) <= 4 and all(seq[g] for g in gap if False) : pass
        # ambiguous: gap contains at least one hot day and <=2 non-hot days total
        nonhot = sum(1 for g in gap if not seq[g])
        hotin = sum(1 for g in gap if seq[g])
        if nonhot <= 2 and hotin >= 1:
            amb_cases.append((c, target_days[e1], target_days[s2], nonhot, hotin))
print("hot run length histogram:", dict(sorted(runlen.items())))
print("ambiguous short-run-between-MHWs cases:", len(amb_cases))
for a in amb_cases[:10]: print(a)

# equality cases (sst exactly == threshold)
eq = (sst == thr[tdoy-1]) & np.isfinite(sst)
print("exact equality days/cells:", int(eq.sum()))

# runs per cell in event window (Aug 5-14) for a few cells in MHW
mhw = np.load("/tmp/mhw_mask.npy")
cols = np.flatnonzero(mhw.reshape(nt,-1).any(axis=0))[:8]
for c in cols:
    seq = flat[:, c]
    idx = np.flatnonzero(np.diff(np.concatenate(([False], seq, [False])).astype(np.int8)))
    starts = idx[0::2]; ends = idx[1::2]-1
    print("cell", c, [(target_days[s], target_days[e], e-s+1) for s,e in zip(starts,ends)])
