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
thr_t = thr[tdoy - 1]
hot = sst >= thr_t
hot[:, ~sea_cells] = False
mhw = np.zeros_like(hot)
flat_hot = hot.reshape(nt, -1); flat_mhw = mhw.reshape(nt, -1)
nruns=0; njoins=0
for c in range(flat_hot.shape[1]):
    seq = flat_hot[:, c]
    if not seq.any(): continue
    idx = np.flatnonzero(np.diff(np.concatenate(([False], seq, [False])).astype(np.int8)))
    starts = idx[0::2]; ends = idx[1::2]-1
    keep=[]
    for s,e in zip(starts,ends):
        if e-s+1 >= 5:
            if keep and s - keep[-1][1] - 1 <= 2:
                keep[-1][1] = e; njoins += 1
            else:
                keep.append([s,e]); nruns += 1
    for s,e in keep: flat_mhw[s:e+1, c] = True
active = flat_mhw.any(axis=1)
ev=[]; i=0
while i < nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        ev.append((target_days[i], target_days[j])); i=j+1
    else: i+=1
print("per-cell runs(>=5d):", nruns, "joins:", njoins)
print("active days:", int(active.sum()))
print("regional events:", ev)
for s,e in ev:
    print(s, "->", e, "length", (date.fromisoformat(e)-date.fromisoformat(s)).days+1)
np.save("/tmp/mhw_mask.npy", mhw)
with open("/tmp/events.txt","w") as fh: fh.write("\n".join(f"{s} {e}" for s,e in ev))
print("hot frac:", hot.mean(), "| mhw frac:", mhw.mean())
# which days are active, and how many cells
for t in np.flatnonzero(active):
    print(target_days[t], int(flat_mhw[t].sum()), "cells in mhw")
