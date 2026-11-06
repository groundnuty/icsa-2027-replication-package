import numpy as np, datetime

target = np.load("/tmp/mhw/target.npy")
sea = np.load("/tmp/mhw/sea_cells.npy")
thr_s = np.load("/tmp/mhw/thr_smooth.npy")
full_mask = np.load("/tmp/mhw/full_mask.npy")

# pick a cell that is in the June event
d0 = datetime.date(2007, 6, 1)
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return cum[d.month-1] + d.day
doys = np.array([doy(d0 + datetime.timedelta(days=i)) for i in range(92)])

active_cells = np.where(full_mask.any(axis=0).any(axis=1))[0]
r, c = np.argwhere(sea)[active_cells[0]]
cell_i = len(np.argwhere(sea)[:0])  # placeholder
sea_idx = np.argwhere(sea)
ci = int(np.where((sea_idx[:,0] == r) & (sea_idx[:,1] == c))[0][0])
print("cell lat/lon:", np.load("/tmp/mhw/lat.npy")[r], np.load("/tmp/mhw/lon.npy")[c])
sst = target[:, r, c]
thr = thr_s[ci, doys]
hot = sst >= thr
pat = "".join("#" if x else "." for x in hot)
mk  = "".join("M" if x else "." for x in full_mask[:, r, c])
print("hot:", pat)
print("mask:", mk)

# event boundaries: check active around 2007-06-13/14 and 2007-07-01/02
act = full_mask.any(axis=(1,2))
for dd in ("2007-06-13", "2007-06-14", "2007-07-01", "2007-07-02", "2007-07-07", "2007-07-08"):
    dt = datetime.date.fromisoformat(dd)
    i = (dt - d0).days
    print(dd, "active" if act[i] else "inactive")

# re-verify events from mask one more time
ev = []
i = 0
while i < 92:
    if act[i]:
        j = i
        while j + 1 < 92 and act[j+1]: j += 1
        ev.append((str(d0+datetime.timedelta(days=i)), str(d0+datetime.timedelta(days=j))))
        i = j + 1
    else:
        i += 1
print("re-derived events:", ev)
print("land cells all zero in mask:", bool((~sea).all() == (full_mask[:, : , :] == 0).all() or True))  # explicit check next
print("non-sea cells zero:", bool(np.all(full_mask[:, ~sea] == 0)))
print("sea cells max value check:", full_mask.max(), full_mask.min(), full_mask.dtype)
