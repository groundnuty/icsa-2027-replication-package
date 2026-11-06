import numpy as np, datetime as dt, pickle, time

t0 = time.time()
thr_raw = np.load("output/thr_raw.npy")
clim_raw = np.load("output/clim_raw.npy")
tgt = np.load("output/tgt_sst.npy").astype(np.float64)
tgt_days = pickle.load(open("output/tgt_days.pkl","rb"))

cell_fin = np.isfinite(tgt).all(axis=0)
print("sea cells:", int(cell_fin.sum()))

nan_cells = np.isnan(thr_raw).all(axis=0)
print("cells all-NaN raw thr:", int(nan_cells.sum()),
      "| sea cells affected:", int((nan_cells & cell_fin.ravel()).sum()))

def circ_smooth31(a):
    i = np.arange(366)[:, None]
    idx = (i - 15 + np.arange(31)[None, :] + 1098) % 366
    return a[idx].mean(axis=1)

thr = circ_smooth31(thr_raw)
clim = circ_smooth31(clim_raw)
print("smooth thr nan:", int(np.isnan(thr).sum()),
      "range: %.2f .. %.2f" % (np.nanmin(thr), np.nanmax(thr)))
np.save("output/thr_smooth.npy", thr)
np.save("output/clim_smooth.npy", clim)
np.save("output/cell_fin.npy", cell_fin)

y0 = dt.date(2004,1,1)
doy_t = np.array([(dt.date.fromisoformat(s) - y0).days + 1 for s in tgt_days])
print("target doy range:", int(doy_t.min()), int(doy_t.max()))

sea = cell_fin.ravel()
hot = np.zeros_like(tgt, dtype=bool)
hot[:, sea] = tgt[:, sea] >= thr[doy_t-1][:, sea]
print("hot cell-days:", int(hot.sum()), "frac of sea: %.4f" % (hot[:, sea].sum() / (tgt.shape[0]*sea.sum())))

T = tgt.shape[0]
mask = np.zeros((T, 60*60), dtype=bool)
for c in np.flatnonzero(sea):
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
print("masked cell-days:", int(mask.sum()))
np.save("output/mask.npy", mask)

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
print("regional events (%d):" % len(ev))
for s, e in ev:
    print("  %s -> %s  (%d days)" % (s, e, (dt.date.fromisoformat(e) - dt.date.fromisoformat(s)).days + 1))
pickle.dump(ev, open("output/events.pkl","wb"))
print("DONE %.1f s" % (time.time()-t0))
