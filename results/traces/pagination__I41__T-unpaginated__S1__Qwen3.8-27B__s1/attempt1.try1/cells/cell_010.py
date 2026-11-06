
import numpy as np
d = np.load('/tmp/mhw_stage2.npz')
T, thrs, clim = d['T'], d['thrs'], d['clim']
sea_cells = d['sea_cells']; tdoy = d['tgt_doy']
n_sea = int(d['n_sea'])
print("target days:", len(T), "doy range:", tdoy.min(), tdoy.max())
print("thr NaN count in target doys:", int(np.isnan(thrs[tdoy]).sum()), "of", n_sea*len(T))
bad = np.where(np.isnan(thrs[tdoy]).any(axis=0))[0]
print("cells with NaN thr on any target day:", bad)
print("SST NaN count in target (sea cells):", int(np.isnan(T).sum()))

hot = T >= thrs[tdoy]
print("total hot cell-days:", int(hot.sum()))
print("days with any hot cell:", int(hot.any(axis=1).sum()))

n_days = len(T)
mhw = np.zeros((n_days, n_sea), dtype=np.uint8)
for c in range(n_sea):
    h = hot[:, c]
    starts, ends = [], []
    i = 0
    while i < n_days:
        if h[i]:
            j = i
            while j+1 < n_days and h[j+1]:
                j += 1
            starts.append(i); ends.append(j)
            i = j+1
        else:
            i += 1
    keep = [(s,e) for s,e in zip(starts,ends) if e-s+1 >= 5]
    merged = []
    for s,e in keep:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    for s,e in merged:
        mhw[s:e+1, c] = 1

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "of", n_days)
events = []
i = 0
while i < n_days:
    if active[i]:
        j = i
        while j+1 < n_days and active[j+1]:
            j += 1
        events.append((i, j))
        i = j+1
    else:
        i += 1
from datetime import date, timedelta
t0 = date(2021,6,1)
for s,e in events:
    print("EVENT: %s .. %s (%d days)" % ((t0+timedelta(days=s)).isoformat(), (t0+timedelta(days=e)).isoformat(), e-s+1))
print("num events:", len(events))
np.savez_compressed('/tmp/mhw_stage3.npz', mhw=mhw, events=np.array(events),
                    sea_cells=sea_cells, lat_r=d['lat_r'], lon_r=d['lon_r'])
print("stage3 saved")
