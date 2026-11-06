import numpy as np, datetime as dt
S_tgt = np.load('/work/S_tgt.npy').reshape(92, -1)
thr_s = np.load('/work/thr_s.npy')
sea_cells = np.load('/work/sea_cells.npy')
tgt_doy = np.load('/work/tgt_doy.npy')
tgt_dates = [dt.date.fromisoformat(str(d)) for d in np.load('/work/coords.npz')['target_dates'].astype('datetime64[D]').astype(object)]
nt = len(tgt_dates)

hot = S_tgt >= thr_s[tgt_doy]   # (92, 3600)
print("hot total:", int(hot.sum()), "of", hot.size)

def cell_mhw_days(h):
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    events = []
    for s, e in runs:
        if events and s - events[-1][1] - 1 <= 2:
            events[-1] = (events[-1][0], e)
        else:
            events.append((s, e))
    days = np.zeros(n, dtype=bool)
    for s, e in events:
        days[s:e+1] = True
    return days

mhw = np.zeros((nt, 3600), dtype=bool)
ndays = np.zeros(len(sea_cells), dtype=int)
for k, c in enumerate(sea_cells):
    days = cell_mhw_days(hot[:, c])
    mhw[:, c] = days
    ndays[k] = days.sum()
print("cells with any MHW day:", int((ndays > 0).sum()), "of", len(sea_cells))
print("per-cell MHW days min/max/mean:", ndays.min(), ndays.max(), round(float(ndays.mean()),2))

active = mhw[:, sea_cells].any(axis=1)
print("active days:", int(active.sum()), "of", nt)
evs = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j < nt and active[j]:
            j += 1
        evs.append((i, j-1))
        i = j
    else:
        i += 1
print("regional events:", len(evs))
for s, e in evs:
    print(" ", tgt_dates[s].isoformat(), "->", tgt_dates[e].isoformat(), f"({e-s+1} days)")

np.save('/work/mhw_bool.npy', mhw)
np.save('/work/active.npy', active)
np.save('/work/events.npy', np.array(evs, dtype=int))
print("SAVED")
