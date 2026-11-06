import numpy as np, datetime as dt, json, os, time
t0 = time.time()
hot_cache = np.load('cache/hot.npy')
mhw_cache = np.load('cache/mhw.npy')
raw_thresh = np.load('cache/raw_thresh.npy'); raw_clim = np.load('cache/raw_clim.npy')
sm_t = np.load('cache/sm_thresh.npy'); sm_c = np.load('cache/sm_clim.npy')
tgt = np.load('cache/tgt.npy')
meta = json.load(open('cache/meta.json'))
dates_tgt = [dt.date.fromisoformat(s) for s in meta['dates_tgt']]
NT, NY, NX = tgt.shape
cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def md_doy(d): return int(cum[d.month-1] + d.day)
tgt_doys = np.array([md_doy(d) for d in dates_tgt])
sea = np.isfinite(tgt).all(axis=0)

# --- recompute hot mask from raw threshold + direct smoothing ---
def circ_smooth31(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    win = np.stack([pad[i:i+31] for i in range(366)], axis=0)
    return win.mean(axis=1)
assert np.array_equal(circ_smooth31(raw_thresh), sm_t)
assert np.array_equal(circ_smooth31(raw_clim), sm_c)
hot = tgt >= sm_t[tgt_doys]
assert np.array_equal(hot, hot_cache)
print('hot mask reproduced; land cells hot anywhere:', int(hot[:, ~sea].sum()))

# --- per-cell MHW (vectorised), with full brute-force check on all cells ---
def per_cell_mhw(hcol):
    x = hcol.astype(np.int8); d = np.diff(x)
    starts = np.flatnonzero(d == 1) + 1; ends = np.flatnonzero(d == -1) + 1
    if hcol[0]:  starts = np.r_[0, starts]
    if hcol[-1]: ends = np.r_[ends, NT]
    lens = ends - starts; keep = lens >= 5
    qs, qe = starts[keep], ends[keep]
    mask = np.zeros(NT, dtype=bool)
    if qs.size:
        cs, ce = qs[0], qe[0]
        for k in range(1, qs.size):
            if qs[k] - ce <= 2: ce = qe[k]
            else: mask[cs:ce] = True; cs, ce = qs[k], qe[k]
        mask[cs:ce] = True
    return mask

H = hot.reshape(NT, -1)
M = np.zeros((NT, H.shape[1]), dtype=bool)
for c in range(H.shape[1]):
    if H[:, c].any(): M[:, c] = per_cell_mhw(H[:, c])
mhw = M.reshape(NT, NY, NX)
assert np.array_equal(mhw, mhw_cache)

# brute force on every cell
def runs_of(mask):
    idx = np.flatnonzero(np.diff(np.r_[0, mask.view(np.int8), 0]))
    return list(zip(idx[0::2], idx[1::2]))
mism = 0
for c in range(H.shape[1]):
    q = [(s, e) for s, e in runs_of(H[:, c]) if e - s >= 5]
    merged = []
    for s, e in q:
        if merged and s - merged[-1][1] <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    bf = np.zeros(NT, bool)
    for s, e in merged: bf[s:e] = True
    if not np.array_equal(bf, M[:, c]): mism += 1
print('per-cell MHW reproduced; brute-force mismatches over all %d cells: %d' % (H.shape[1], mism))

# --- regional events ---
active = mhw.any(axis=(1, 2))
ev_runs = runs_of(active)
events = [{'onset': dates_tgt[s].isoformat(), 'end': dates_tgt[e-1].isoformat()} for s, e in ev_runs]
print('events:', events)
hd = hot.reshape(NT, -1).sum(axis=1); md_ = mhw.reshape(NT, -1).sum(axis=1)
print('day: hot_cells / mhw_cells (all 92 days):')
for i, d in enumerate(dates_tgt):
    print('  %s hot=%4d mhw=%4d' % (d, hd[i], md_[i]))
