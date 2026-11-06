import numpy as np
from datetime import date, timedelta

z = np.load('work/sst.npz')
ST = z['ST']; tt = z['tt']
z2 = np.load('work/thr.npz')
thr_s, sea = z2['thr_s'], z2['sea']
n_cells = 3600
STf = ST.reshape(92, n_cells)

# day of year for target dates (leap-year mapping)
doy_md = {}
d = date(2004, 1, 1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day)
    d += timedelta(days=1)
md_to_doy = {v: k for k, v in doy_md.items()}
t_doys = []
for ts in tt:
    dd = date.fromisoformat(ts.astype('datetime64[D]').astype(str))
    t_doys.append(md_to_doy[(dd.month, dd.day)])
t_doys = np.array(t_doys)
print("target doys:", t_doys[0], t_doys[-1], "n:", len(t_doys))

hot = np.zeros((92, n_cells), dtype=bool)
for ti in range(92):
    thr_col = thr_s[:, t_doys[ti]-1]
    hot[ti] = STf[ti] >= thr_col     # NaN threshold -> False
print("hot fraction (sea cells):", hot[:, sea].mean())

def mhw_mask(hot_row):
    d = np.diff(np.concatenate(([0], hot_row.view(np.int8), [0])))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0] - 1
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    mask = np.zeros(len(hot_row), dtype=bool)
    if len(starts):
        s0, e0 = starts[0], ends[0]
        for s, e in zip(starts[1:], ends[1:]):
            if s - e0 - 1 <= 2:
                e0 = e
            else:
                mask[s0:e0+1] = True
                s0, e0 = s, e
        mask[s0:e0+1] = True
    return mask

# brute-force reference for a few cells
def mhw_mask_ref(hot_row):
    n = len(hot_row)
    runs = []
    i = 0
    while i < n:
        if hot_row[i]:
            j = i
            while j+1 < n and hot_row[j+1]: j += 1
            runs.append((i, j)); i = j+1
        else: i += 1
    runs = [(s,e) for s,e in runs if e-s+1 >= 5]
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    mask = np.zeros(n, bool)
    for s,e in merged: mask[s:e+1] = True
    return mask

for c in list(range(0, n_cells, 211)) + [0, 500, 3302]:
    a = mhw_mask(hot[:, c]); b = mhw_mask_ref(hot[:, c])
    assert (a == b).all(), c
print("per-cell MHW algorithm verified against independent reference")

mask_cells = np.zeros((n_cells, 92), dtype=bool)
for c in np.where(sea)[0]:
    mask_cells[c] = mhw_mask(hot[:, c])
print("cells with >=1 MHW day:", int(mask_cells.sum(axis=1).gt(0).sum()), "of", int(sea.sum()))

active = mask_cells.any(axis=0)
dd = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
starts = np.where(dd == 1)[0]; ends = np.where(dd == -1)[0] - 1
events = [(str(tt[s].astype('datetime64[D]')), str(tt[e].astype('datetime64[D]'))) for s, e in zip(starts, ends)]
print("regional events:", events)
print("active days:", int(active.sum()))

np.savez('work/mhw.npz', mask=mask_cells.astype(np.uint8), active=active, hot=hot)
print("saved work/mhw.npz")
