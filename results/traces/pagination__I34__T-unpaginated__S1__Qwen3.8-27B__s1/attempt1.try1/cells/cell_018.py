import numpy as np, datetime

target = np.load("/tmp/mhw/target.npy")
sea = np.load("/tmp/mhw/sea_cells.npy")
sea_idx = np.argwhere(sea)
thr_s = np.load("/tmp/mhw/thr_smooth.npy")

d0 = datetime.date(2007, 6, 1)
ndays = target.shape[0]
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d):
    return cum[d.month-1] + d.day

doys = np.array([doy(d0 + datetime.timedelta(days=i)) for i in range(ndays)])
sst_sea = target[:, sea_idx[:,0], sea_idx[:,1]]
hot = sst_sea.T >= thr_s[:, doys]
print("hot fraction:", hot.mean())

mask = np.zeros((len(sea_idx), ndays), dtype=np.uint8)
n_runs_all = 0
for c in range(len(sea_idx)):
    h = hot[c]
    if not h.any():
        continue
    diff = np.diff(h.astype(np.int8))
    starts = list(np.where(diff == 1)[0] + 1)
    if h[0]: starts.insert(0, 0)
    ends = list(np.where(diff == -1)[0])
    if h[-1]: ends.append(ndays - 1)
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for s, e in merged:
        mask[c, s:e+1] = 1
        n_runs_all += 1

full_mask = np.zeros((ndays, 60, 60), dtype=np.uint8)
full_mask[:, sea_idx[:,0], sea_idx[:,1]] = mask.T
print("merged per-cell MHW count:", n_runs_all)
print("mhw cell-days:", int(full_mask.sum()), "of", full_mask.size)

active = mask.any(axis=0)
events = []
i = 0
while i < ndays:
    if active[i]:
        j = i
        while j + 1 < ndays and active[j+1]:
            j += 1
        events.append((str(d0 + datetime.timedelta(days=i)), str(d0 + datetime.timedelta(days=j)), j - i + 1))
        i = j + 1
    else:
        i += 1
print("regional events:")
for ev in events:
    print("  ", ev[0], "->", ev[1], "len", ev[2])
print("active first 12:", active[:12].astype(int))
print("active last 12:", active[-12:].astype(int))

np.save("/tmp/mhw/full_mask.npy", full_mask)
np.save("/tmp/mhw/events.npy", np.array(events, dtype=object), allow_pickle=True)
print("saved")
