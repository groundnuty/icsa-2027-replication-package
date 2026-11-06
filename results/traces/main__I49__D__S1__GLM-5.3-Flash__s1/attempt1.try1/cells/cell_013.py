import numpy as np, datetime as dt

cube_t = np.load('/work/cube_t.npy')
thresh_s = np.load('/work/thresh_s.npy')
dates_t = [dt.date.fromisoformat(l.strip()) for l in open('/work/dates_t.txt') if l.strip()]
def doy_md(d): return dt.date(2000, d.month, d.day).timetuple().tm_yday
doy_t = np.array([doy_md(d) for d in dates_t])
hot = cube_t >= thresh_s[doy_t - 1]

# exact-equality check (SST == threshold)
eq = (cube_t == thresh_s[doy_t - 1]) & np.isfinite(cube_t)
print("days where SST exactly equals threshold:", int(eq.sum()))

def per_cell_mhw_mask(h):
    idx = np.flatnonzero(h)
    if idx.size == 0: return np.zeros_like(h)
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[0, breaks+1]; ends = np.r_[breaks, idx.size-1]
    events = []
    for s, e in zip(starts, ends):
        if idx[e]-idx[s]+1 < 5: continue
        rs, re = idx[s], idx[e]
        if events and rs - events[-1][1] - 1 <= 2: events[-1] = (events[-1][0], re)
        else: events.append((rs, re))
    m = np.zeros_like(h)
    for s,e in events: m[s:e+1] = True
    return m

def brute_mask(h):
    """Simple independent implementation: scan runs, drop <5, join gaps<=2, iteratively from scratch."""
    T = len(h)
    runs = []
    i = 0
    while i < T:
        if h[i]:
            j = i
            while j+1 < T and h[j+1]: j += 1
            runs.append([i, j]); i = j+1
        else:
            i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    # join gaps <=2 repeatedly
    merged = []
    for r in runs:
        if merged and r[0]-merged[-1][1]-1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    m = np.zeros(T, bool)
    for s,e in merged: m[s:e+1] = True
    return m

# compare on all cells
nlat, nlon = hot.shape[1:]
mismatch = 0
for i in range(nlat):
    for j in range(nlon):
        a = per_cell_mhw_mask(hot[:,i,j]); b = brute_mask(hot[:,i,j])
        if not np.array_equal(a,b): mismatch += 1
print("cells where vectorized != brute force:", mismatch)

# stats of per-cell MHWs
mhw_all = np.zeros_like(hot)
counts = np.zeros((nlat,nlon), int)
durs = []
for i in range(nlat):
    for j in range(nlon):
        h = hot[:,i,j]
        m = per_cell_mhw_mask(h)
        mhw_all[:,i,j] = m
        if m.any():
            idx = np.flatnonzero(m); br = np.flatnonzero(np.diff(idx)>1)
            st = np.r_[0, br+1]; en = np.r_[br, idx.size-1]
            counts[i,j] = len(st)
            durs += [idx[e]-idx[s]+1 for s,e in zip(st,en)]
durs = np.array(durs)
print("total per-cell MHW events:", durs.size, "| duration min/median/max:", durs.min(), np.median(durs), durs.max())
print("MHWs per sea cell: min/median/max:", counts[hot[0].size and True].min(), np.median(counts[counts>0]), counts.max())
print("mhw mask total cell-days:", int(mhw_all.sum()))
print("land cells all zero in mhw?", not mhw_all[:, ~np.isfinite(cube_t).all(axis=0)].any())

# regional events again + a couple of spot checks of active-day logic
active = mhw_all.any(axis=(1,2))
idx = np.flatnonzero(active)
br = np.flatnonzero(np.diff(idx)>1); st = np.r_[0,br+1]; en = np.r_[br, idx.size-1]
events = [(dates_t[idx[s]], dates_t[idx[e]]) for s,e in zip(st,en)]
print("events:", [(a.isoformat(), b.isoformat(), (b-a).days+1) for a,b in events])
# active day coverage: how many cells active on first day of each event
for a,b in events:
    k = dates_t.index(a)
    print(f"  {a}: cells in MHW on onset day = {int(mhw_all[k].sum())}")
