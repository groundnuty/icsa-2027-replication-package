import numpy as np, datetime as dt, pickle, time, json, warnings

t0 = time.time()
warnings.filterwarnings("ignore")

bas = np.load("output/bas_sst.npy").astype(np.float64)
tgt = np.load("output/tgt_sst.npy").astype(np.float64)
with open("output/bas_days.pkl", "rb") as fh: bas_days = pickle.load(fh)
with open("output/tgt_days.pkl", "rb") as fh: tgt_days = pickle.load(fh)
b_ord_arr = np.array([dt.date.fromisoformat(d).toordinal() for d in bas_days])
b0 = b_ord_arr[0]

cell_fin = np.isfinite(tgt).all(axis=0)
n_sea = int(cell_fin.sum())
print("sea cells:", n_sea)

baseline_years = list(range(1992, 2003))
def isleap(y): return (y % 4 == 0) and (y % 100 != 0 or y % 400 == 0)

thr_raw = np.full((366, 60*60), np.nan)
clim_raw = np.full((366, 60*60), np.nan)
pool_sizes = {}
for d in range(1, 367):
    if d == 60:
        continue
    b_dates = []
    for y in baseline_years:
        if d <= 365:
            b = dt.date(y,1,1) + dt.timedelta(days=d-1)
        else:
            if isleap(y):
                b = dt.date(y,12,31)
            else:
                continue
        b_dates.append(b)
    idx_set = set()
    for b in b_dates:
        o = b.toordinal()
        for k in range(-5, 6):
            idx_set.add(o + k)
    idx = np.array(sorted(idx_set))
    assert idx.min() >= b0 and idx.max() <= b_ord_arr[-1]
    vals = bas[idx - b0].reshape(len(idx), -1)
    thr_raw[d-1] = np.nanquantile(vals, 0.9, method="hazen", axis=0)
    clim_raw[d-1] = np.nanmean(vals, axis=0)
    pool_sizes[d] = len(idx)
print("pools done %.1f s" % (time.time()-t0))
print("pool sizes sample:", {k: pool_sizes[k] for k in (1, 59, 61, 183, 365, 366)})

# day 60 = mean of 59 and 61
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

# fully-NaN pools: which cells?
nan_cells = np.isnan(thr_raw).all(axis=0) | np.isnan(clim_raw).all(axis=0)
print("cells with all-NaN raw thr:", int(nan_cells.sum()), "| overlap with non-sea:", int((nan_cells & ~cell_fin).sum()), "| sea cells affected:", int((nan_cells & cell_fin).sum()))

# ---- 31-day centred circular moving mean over 366 days
def circ_smooth31(a):
    i = np.arange(366)[:, None]
    idx = (i - 15 + np.arange(31)[None, :] + 366*3) % 366
    return a[idx].mean(axis=1)

thr = circ_smooth31(thr_raw)
clim = circ_smooth31(clim_raw)
print("smooth done; thr nan count:", int(np.isnan(thr).sum()))
np.save("output/thr_smooth.npy", thr)
np.save("output/clim_smooth.npy", clim)
np.save("output/cell_fin.npy", cell_fin)

# ---- target day-of-year (2004 is leap)
y0 = dt.date(2004,1,1)
doy_t = np.array([(dt.date.fromisoformat(s) - y0).days + 1 for s in tgt_days])
print("target doy range:", doy_t.min(), doy_t.max())

hot = np.zeros_like(tgt, dtype=bool)
hot[:, cell_fin.ravel()] = tgt[:, cell_fin.ravel()] >= thr[doy_t-1][:, cell_fin.ravel()]
print("hot days total:", int(hot.sum()), "fraction:", float(hot.mean()))

# ---- per-cell MHW: runs >=5 hot days, merge gaps of 1-2
T = tgt.shape[0]
mask = np.zeros((T, 60*60), dtype=bool)
for c in range(60*60):
    h = hot[:, c]
    if not h.any():
        continue
    diff = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts = np.flatnonzero(diff == 1)
    ends = np.flatnonzero(diff == -1)
    runs = [(s, e) for s, e in zip(starts, ends) if e - s >= 5]
    if not runs:
        continue
    events = []
    for s, e in runs:
        if events and s - events[-1][1] <= 2:
            events[-1][1] = e
        else:
            events.append([s, e])
    for s, e in events:
        mask[s:e, c] = True
print("mask done %.1f s, masked cell-days:" % time.time(), int(mask.sum()))
np.save("output/mask.npy", mask)

# ---- regional events
active = mask.any(axis=1)
ev = []
d = 0
while d < T:
    if active[d]:
        e = d
        while e + 1 < T and active[e+1]:
            e += 1
        ev.append((tgt_days[d], tgt_days[e]))
        d = e + 1
    else:
        d += 1
print("regional events:")
for s, e in ev:
    print("  ", s, "->", e, "(%d days)" % (len(ev) and ((dt.date.fromisoformat(e) - dt.date.fromisoformat(s)).days + 1)))
with open("output/events.pkl", "wb") as fh:
    pickle.dump(ev, fh)
print("ALL DONE %.1f s" % (time.time()-t0))
