import numpy as np
from datetime import date, timedelta

block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")
thr = np.load("/tmp/thr_smooth.npy")   # (366, 60, 60) float64
nb = 4028
target_days = alldays[nb:]              # 92 days
nt = len(target_days)

cum = [0,31,59,90,120,151,181,212,243,273,304,334]
def doy_of(s):
    y,m,d = int(s[:4]), int(s[5:7]), int(s[8:10])
    if m == 2 and d == 29: return 60
    return cum[m-1] + d
tdoy = np.array([doy_of(s) for s in target_days])
print("target doys:", tdoy.min(), "..", tdoy.max())

sst = block[nb:].astype(np.float64)     # (92, 60, 60) float64
thr_t = thr[tdoy - 1]                   # (92, 60, 60) threshold per day
hot = sst >= thr_t                      # NaN comparisons -> False
print("hot fraction over all cells:", hot.mean())
hot[:, ~sea_cells] = False              # land cells never hot (also NaN anyway)
print("hot days count per-cell max:", hot.sum(axis=0).max())

# per-cell MHW: runs >=5 hot days, join gaps of 1-2 non-hot days
mhw = np.zeros_like(hot)                # bool (92, 3600)
flat_hot = hot.reshape(nt, -1)
flat_mhw = mhw.reshape(nt, -1)
nruns_kept = 0; njoins = 0
for c in range(flat_hot.shape[1]):
    seq = flat_hot[:, c]
    if not seq.any(): continue
    # run-length encode True runs
    idx = np.flatnonzero(np.diff(np.concatenate(([False], seq, [False])).astype(np.int8)))
    starts = idx[0::2]; ends = idx[1::2] - 1   # inclusive ends
    keep = []
    for s, e in zip(starts, ends):
        if e - s + 1 >= 5:
            if keep and s - keep[-1][1] - 1 <= 2:
                keep[-1][1] = e; njoins += 1
            else:
                keep.append([s, e]); nruns_kept += 1
    for s, e in keep:
        flat_mhw[s:e+1, c] = True
print("runs kept (>=5d):", nruns_kept, "joins:", njoins)

# regional: active if any cell in MHW that day
active = flat_mhw.any(axis=1)
print("active days:", int(active.sum()), "of", nt)
# events = maximal runs of consecutive active days
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j + 1 < nt and active[j+1]: j += 1
        ev.append((target_days[i], target_days[j]))
        i = j + 1
    else:
        i += 1
print("regional events:", ev)
for s, e in ev:
    d0 = date.fromisoformat(s); d1 = date.fromisoformat(e)
    print(s, "->", e, "length", (d1-d0).days+1)

np.save("/tmp/mhw_mask.npy", mhw.reshape(nt, 60, 60))
with open("/tmp/events.txt", "w") as fh:
    fh.write("\n".join(f"{s} {e}" for s, e in ev))
# stats for report
mhw_f = mhw.reshape(nt, -1)
print("cells in mhw per day (min/max):", mhw_f.sum(axis=1).min(), mhw_f.sum(axis=1).max())
print("per-cell mhw day counts: max", mhw_f.sum(axis=0).max(), "mean", mhw_f.sum(axis=0).mean())
