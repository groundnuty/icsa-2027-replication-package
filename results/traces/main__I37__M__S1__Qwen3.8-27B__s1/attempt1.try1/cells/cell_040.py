import time, datetime as dt, json
import numpy as np

t0 = time.time()
ext = np.load('/work/chk/ext.npy').astype(np.float64)
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')
thr_saved = np.load('/work/chk/thr.npy')
clim_saved = np.load('/work/chk/clim.npy')

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in tgt_dates])
doy_b = doy_ext[5:5+4018]
print("doy target:", doy_tgt.min(), "-", doy_tgt.max())

# recompute raw threshold/climatology (independent pass to verify saved arrays)
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    js = np.where(doy_b == d)[0]
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
    pool = ext[rows]
    thr_raw[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim_raw[d-1] = np.nanmean(pool, axis=0)
thr_raw[59] = 0.5 * (thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5 * (clim_raw[58] + clim_raw[60])
def smooth31(a):
    acc = np.zeros_like(a)
    for k in range(-15, 16):
        acc += np.roll(a, -k, axis=0)
    return acc / 31.0
thr = smooth31(thr_raw)
clim = smooth31(clim_raw)
print("verify vs saved thr: max abs diff =", np.nanmax(np.abs(thr - thr_saved)),
      " clim diff =", np.nanmax(np.abs(clim - clim_saved)))
assert np.allclose(thr, thr_saved, equal_nan=True) and np.allclose(clim, clim_saved, equal_nan=True)
print("recompute verified in", time.time()-t0)
np.save('/work/chk/thr.npy', thr); np.save('/work/chk/clim.npy', clim)

# --- hot days ---
hot = np.zeros((92, 60, 60), bool)
for t in range(92):
    d0 = doy_tgt[t] - 1
    hot[t] = sea & (tgt[t] >= thr[d0])
print("hot day-cells total:", int(hot.sum()), " active days (any cell hot):", int(hot.any(axis=(1,2)).sum()))

# --- per-cell MHWs with gap joining ---
mhw = np.zeros((92, 60, 60), np.uint8)
sea_cells = np.argwhere(sea)
n_cell_mhw = 0
for (i, j) in sea_cells:
    b = hot[:, i, j]
    if not b.any():
        continue
    b8 = b.view(np.int8)
    dd = np.diff(np.concatenate(([0], b8, [0])))
    starts = np.flatnonzero(dd == 1)
    ends = np.flatnonzero(dd == -1) - 1
    lens = ends - starts + 1
    seeds = np.flatnonzero(lens >= 5)
    if seeds.size == 0:
        continue
    cur_s, cur_e = int(starts[seeds[0]]), int(ends[seeds[0]])
    for sidx in seeds[1:]:
        s, e = int(starts[sidx]), int(ends[sidx])
        if s - cur_e - 1 <= 2:
            cur_e = max(cur_e, e)
        else:
            mhw[cur_s:cur_e+1, i, j] = 1
            n_cell_mhw += 1
            cur_s, cur_e = s, e
    mhw[cur_s:cur_e+1, i, j] = 1
    n_cell_mhw += 1
print("per-cell MHWs:", n_cell_mhw)

# --- regional events ---
active = mhw.any(axis=(1,2))
events = []
a8 = active.view(np.int8)
dd = np.diff(np.concatenate(([0], a8, [0])))
starts = np.flatnonzero(dd == 1)
ends = np.flatnonzero(dd == -1) - 1
for s, e in zip(starts, ends):
    events.append({"onset": tgt_dates[int(s)].isoformat(), "end": tgt_dates[int(e)].isoformat()})
print("regional events:", len(events))
for ev in events:
    print("  ", ev["onset"], "->", ev["end"])
print("active days:", int(active.sum()))
json.dump({'events': events, 'n_cell_mhw': n_cell_mhw, 'active_days': int(active.sum())},
          open('/work/chk/events.json', 'w'))
print("stage done in", time.time()-t0)
