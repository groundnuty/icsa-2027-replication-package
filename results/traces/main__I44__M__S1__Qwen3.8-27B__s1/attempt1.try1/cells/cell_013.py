import numpy as np, datetime as dt, pickle, time

t0 = time.time()
thr = np.load("output/thr_smooth.npy")
clim = np.load("output/clim_smooth.npy")
tgt3 = np.load("output/tgt_sst.npy").astype(np.float64)
tgt_days = pickle.load(open("output/tgt_days.pkl","rb"))

T = tgt3.shape[0]
tgt = tgt3.reshape(T, 3600)
cell_fin = np.isfinite(tgt).all(axis=0)
print("sea cells:", int(cell_fin.sum()))

def circ_smooth31(a):
    i = np.arange(366)[:, None]
    idx = (i - 15 + np.arange(31)[None, :] + 1098) % 366
    return a[idx].mean(axis=1)
# verify saved smoothing matches recomputation from raw (sanity)
thr_check = circ_smooth31(np.load("output/thr_raw.npy"))
assert np.allclose(thr, thr_check, equal_nan=True)
print("smoothing sanity OK")

y0 = dt.date(2004,1,1)
doy_t = np.array([(dt.date.fromisoformat(s) - y0).days + 1 for s in tgt_days])
print("target doy range:", int(doy_t.min()), int(doy_t.max()))

sea = cell_fin
hot = np.zeros((T, 3600), dtype=bool)
hot[:, sea] = tgt[:, sea] >= thr[doy_t-1][:, sea]
print("hot cell-days:", int(hot.sum()), "frac of sea: %.4f" % (hot[:, sea].sum() / (T*sea.sum())))

mask = np.zeros((T, 3600), dtype=bool)
n_mhw_cells = 0
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
    n_mhw_cells += 1
    events = []
    for s, e in runs:
        if events and s - events[-1][1] <= 2:
            events[-1][1] = e
        else:
            events.append([s, e])
    for s, e in events:
        mask[s:e, c] = True
print("cells with >=1 per-cell MHW:", n_mhw_cells)
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
