import numpy as np
from itertools import groupby
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
mz = np.load('/work/mhw_intermediate.npz', allow_pickle=False)
mask = mz['mask']; sea = mz['sea']
tc = np.load('/work/thr_cli.npz', allow_pickle=False)
thr_s = tc['thr_s']
d2i = {d: i for i, d in enumerate(dates)}
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]
cum=[0]
for m in mdays: cum.append(cum[-1]+m)
def doy(s): return cum[int(s[5:7])-1] + int(s[8:10])
tgt_dates = [str(d) for d in mz['tgt_dates']]
tdoy = np.array([doy(s) for s in tgt_dates])
tgt = A[d2i['2010-06-01']:d2i['2010-08-31']+1]
sea_cells = np.argwhere(sea)
N = len(tgt_dates)

def mhw_mask_independent(h):
    # h: 1D bool
    segs = [(k, list(g)) for k, g in groupby(h)]
    # hot runs: (start, end)
    hot_runs = []
    pos = 0
    starts_all = []
    for k, g in segs:
        L = len(g)
        if k:
            hot_runs.append((pos, pos+L-1))
        pos += L
    cands = [r for r in hot_runs if r[1]-r[0]+1 >= 5]
    merged = []
    for r in cands:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(list(r))
    m = np.zeros(len(h), bool)
    for (s, e) in merged:
        m[s:e+1] = True
    return m

mism = 0
maxdur = 0
ndurs = []
for c in range(len(sea_cells)):
    h = np.array([(tgt[t] >= thr_s[tdoy[t]])[sea_cells[c,0], sea_cells[c,1]] for t in range(N)])
    m2 = mhw_mask_independent(h)
    if not np.array_equal(m2, mask[:, c]):
        mism += 1
        if mism <= 3:
            print("MISMATCH at cell", c, np.where(m2 ^ mask[:, c])[0])
    durs = [(e-s+1) for (s,e) in [(s_,e_) for s_,e_ in []]]
print("mismatches:", mism, "of", len(sea_cells))

# distribution of merged MHW durations per cell
durs = []
for c in range(len(sea_cells)):
    h = np.array([(tgt[t] >= thr_s[tdoy[t]])[sea_cells[c,0], sea_cells[c,1]] for t in range(N)])
    m2 = mhw_mask_independent(h)
    # merged block durations
    i = 0
    while i < N:
        if m2[i]:
            s = i
            while i < N and m2[i]: i += 1
            durs.append(i-s)
        else:
            i += 1
import collections
print("num merged MHW blocks total:", len(durs))
print("duration hist:", dict(sorted(collections.Counter(durs).items())))
