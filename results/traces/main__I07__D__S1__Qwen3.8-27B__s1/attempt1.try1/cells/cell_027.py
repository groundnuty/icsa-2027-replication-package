import numpy as np
from datetime import date, timedelta
S_tgt = np.load('/work/S_tgt.npy')
thr_s = np.load('/work/thr_s.npy')

tgt_dates = []
d = date(2021,6,1)
while d <= date(2021,8,31):
    tgt_dates.append(d); d += timedelta(days=1)
def doy_of(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1
doy_tgt = np.array([doy_of(dt) for dt in tgt_dates])

hot = S_tgt >= thr_s[doy_tgt-1].reshape(len(doy_tgt), 60, 60)
sea = np.isfinite(S_tgt).all(axis=0).reshape(-1)
land = ~sea
hflat = hot.reshape(len(doy_tgt), 3600)
print("hot frac (sea):", hflat[:, sea].mean(), " hot on land:", hflat[:, land].sum())

Nt = len(doy_tgt)
mask = np.zeros((Nt, 60, 60), dtype=np.uint8)
n_mhw_per_cell = np.zeros(3600, dtype=int)
for c in np.where(sea)[0]:
    h = hflat[:, c]
    padded = np.concatenate(([0], h.astype(np.int8), [0]))
    dd = np.diff(padded)
    starts = np.where(dd == 1)[0]
    ends = np.where(dd == -1)[0] - 1
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    n_mhw_per_cell[c] = len(merged)
    for s, e in merged:
        mask[s:e+1, c//60, c%60] = 1

print("cells with >=1 MHW:", (n_mhw_per_cell > 0).sum(), "of", sea.sum())
print("MHWs per cell min/max/mean:", n_mhw_per_cell.min(), n_mhw_per_cell.max(), round(n_mhw_per_cell[sea].mean(),3))

active = mask.any(axis=(1, 2))
print("active days:", int(active.sum()), "of", Nt)
padded = np.concatenate(([False], active, [False]))
dd = np.diff(padded.astype(np.int8))
s_idx = np.where(dd == 1)[0]
e_idx = np.where(dd == -1)[0] - 1
events = [(int(s), int(e)) for s, e in zip(s_idx, e_idx)]
for s, e in events:
    print("event:", tgt_dates[s], "->", tgt_dates[e], f"({e-s+1} days)")
np.save('/work/mask.npy', mask)
np.save('/work/events.npy', np.array(events, dtype=int).reshape(-1, 2) if events else np.zeros((0,2), dtype=int))
