import numpy as np, datetime as dt
S_tgt = np.load('/work/S_tgt.npy')
thr_s = np.load('/work/thr_s.npy')
sea_cells = np.load('/work/sea_cells.npy')
tgt_doy = np.load('/work/tgt_doy.npy')
tgt_dates = [dt.date.fromisoformat(str(d)) for d in np.load('/work/coords.npz')['target_dates'].astype('datetime64[D]').astype(object)]
nt = len(tgt_dates)
print("target days:", nt, tgt_dates[0], tgt_dates[-1], "doys", tgt_doy.min(), tgt_doy.max())

hot = S_tgt >= thr_s[tgt_doy][:, None, :]   # (nt, 60, 60) broadcast; only sea cells matter
hot = hot.reshape(nt, -1)
print("hot shape:", hot.shape, "total hot days (all cells):", int(hot.sum()))

def cell_mhw_days(h):
    """h: bool array length nt. Returns set of day indices inside per-cell MHWs
    (runs >=5 hot, joined across gaps of 1-2 non-hot days, gap days included)."""
    n = len(h)
    # maximal hot runs
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
    # merge across gaps of 1-2
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
n_events_per_cell = np.zeros(len(sea_cells), dtype=int)
for k, c in enumerate(sea_cells):
    days = cell_mhw_days(hot[:, c])
    mhw[:, c] = days
    n_events_per_cell[k] = days.sum()
print("cells with any MHW day:", int((n_events_per_cell > 0).sum()))
print("MHW day count: min/max/mean over cells:", n_events_per_cell.min(), n_events_per_cell.max(), round(float(n_events_per_cell.mean()),2))

active = mhw[:, sea_cells].any(axis=1)
print("active days:", int(active.sum()), "of", nt)
# regional events: maximal runs of consecutive active days
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
