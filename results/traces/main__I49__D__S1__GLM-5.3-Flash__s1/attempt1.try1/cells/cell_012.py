import numpy as np, datetime as dt, json, os

cube_t = np.load('/work/cube_t.npy')
thresh_s = np.load('/work/thresh_s.npy')
clim_s = np.load('/work/clim_s.npy')
dates_t = [dt.date.fromisoformat(l.strip()) for l in open('/work/dates_t.txt') if l.strip()]
T = len(dates_t)

def doy_md(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday
doy_t = np.array([doy_md(d) for d in dates_t])
print("target:", dates_t[0], "->", dates_t[-1], "| T =", T, "| doys", doy_t[0], "...", doy_t[-1])

# hot days: SST >= threshold (NaN >= x is False -> land cells never hot)
hot = cube_t >= thresh_s[doy_t - 1]          # (T, nlat, nlon) bool
print("hot day fraction (all cells):", hot.mean())

def per_cell_mhw_mask(h):
    """h: (T,) bool for one cell -> (T,) bool mask of per-cell MHW membership."""
    idx = np.flatnonzero(h)
    if idx.size == 0:
        return np.zeros_like(h)
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[0, breaks + 1]
    ends = np.r_[breaks, idx.size - 1]
    events = []  # (start_idx, end_idx) inclusive, only qualifying runs joined
    for s, e in zip(starts, ends):
        run_len = idx[e] - idx[s] + 1
        if run_len < 5:
            continue
        rs, re = idx[s], idx[e]
        if events and (rs - events[-1][1] - 1) <= 2:
            events[-1] = (events[-1][0], re)
        else:
            events.append((rs, re))
    m = np.zeros_like(h)
    for s, e in events:
        m[s:e+1] = True
    return m

nlat, nlon = hot.shape[1:]
mhw = np.zeros_like(hot)
n_events_cells = 0
for i in range(nlat):
    for j in range(nlon):
        m = per_cell_mhw_mask(hot[:, i, j])
        mhw[:, i, j] = m
        if m.any():
            n_events_cells += 1
print("cells with >=1 per-cell MHW:", n_events_cells, "of", hot[0].size)
print("mhw days-cell count:", int(mhw.sum()))

# regional: active = any cell inside a per-cell MHW
active = mhw.any(axis=(1, 2))
print("active days:", int(active.sum()), "of", T)
# regional events: maximal runs of consecutive active days
events = []
idx = np.flatnonzero(active)
if idx.size:
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[0, breaks + 1]
    ends = np.r_[breaks, idx.size - 1]
    for s, e in zip(starts, ends):
        events.append({"onset": dates_t[idx[s]].isoformat(), "end": dates_t[idx[e]].isoformat()})
for ev in events:
    ev["days"] = (dt.date.fromisoformat(ev["end"]) - dt.date.fromisoformat(ev["onset"])).days + 1
print("regional events:", len(events))
for ev in events:
    print(" ", ev)

# gaps between events (non-active days)
inact = np.flatnonzero(~active)
print("non-active days:", len(inact), (dates_t[inact[0]].isoformat(), dates_t[inact[-1]].isoformat()) if len(inact) else "")

# quick sanity: activity timeline compressed
tl = "".join("#" if a else "." for a in active)
print("timeline (#=active):")
for k in range(0, T, 92):
    print(" ", dates_t[k].isoformat(), tl[k:k+92])
