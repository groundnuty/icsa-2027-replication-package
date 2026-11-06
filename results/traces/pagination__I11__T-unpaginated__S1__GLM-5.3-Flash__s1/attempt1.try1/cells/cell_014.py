import numpy as np, datetime as dt, json, time
t0 = time.time()
hot = np.load('cache/hot.npy')          # (92, 60, 60) bool
tgt = np.load('cache/tgt.npy')
meta = json.load(open('cache/meta.json'))
dates_tgt = [dt.date.fromisoformat(s) for s in meta['dates_tgt']]
NT, NY, NX = hot.shape
sea = np.isfinite(tgt).all(axis=0)

mhw = np.zeros((NT, NY, NX), dtype=bool)

def per_cell_mhw(hcol):                 # hcol: (92,) bool -> mask (92,) bool
    x = hcol.astype(np.int8)
    d = np.diff(x)
    starts = np.flatnonzero(d == 1) + 1
    ends   = np.flatnonzero(d == -1) + 1            # exclusive
    if hcol[0]:  starts = np.r_[0, starts]
    if hcol[-1]: ends   = np.r_[ends, NT]
    lens = ends - starts
    keep = lens >= 5
    qs, qe = starts[keep], ends[keep]
    mask = np.zeros(NT, dtype=bool)
    if qs.size:
        cs, ce = qs[0], qe[0]
        for k in range(1, qs.size):
            if qs[k] - ce <= 2:                     # 1 or 2 non-hot days between
                ce = qe[k]
            else:
                mask[cs:ce] = True
                cs, ce = qs[k], qe[k]
        mask[cs:ce] = True
    return mask

# vector-of-cells loop
H = hot.reshape(NT, -1)
M = np.zeros((NT, H.shape[1]), dtype=bool)
for c in range(H.shape[1]):
    if H[:, c].any():
        M[:, c] = per_cell_mhw(H[:, c])
mhw = M.reshape(NT, NY, NX)

print('per-cell MHW cell-days:', int(mhw.sum()), '| cells with >=1 MHW day:', int(mhw.any(axis=0).sum()))
print('hot days not inside MHW (cell-days):', int((hot & ~mhw).sum()))
print('non-hot days inside MHW (gap days):', int((~hot & mhw).sum()))

# cross-check with an independent per-cell implementation via scipy-free events listing
def runs_of(mask):
    idx = np.flatnonzero(np.diff(np.r_[0, mask.view(np.int8), 0]))
    return list(zip(idx[0::2], idx[1::2]))          # [start, end) pairs
# verify on 200 random cells that merging logic == brute-force recompute
rng = np.random.default_rng(1)
mism = 0
for c in rng.choice(H.shape[1], 200, replace=False):
    col = H[:, c]
    # brute force: find qualifying runs, merge pairwise chains
    rs = runs_of(col)
    q = [(s, e) for s, e in rs if e - s >= 5]
    merged = []
    for s, e in q:
        if merged and s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    bf = np.zeros(NT, bool)
    for s, e in merged: bf[s:e] = True
    if not np.array_equal(bf, M[:, c]): mism += 1
print('brute-force cross-check mismatches (200 random cells):', mism)

# active days & regional events
active = mhw.any(axis=(1, 2))
ev_runs = runs_of(active)
events = [{'onset': dates_tgt[s].isoformat(), 'end': dates_tgt[e-1].isoformat()} for s, e in ev_runs]
print('active days:', int(active.sum()), 'of', NT)
for s, e in ev_runs:
    seg = mhw[s:e]
    print('event %s .. %s (%d days): cells-in-MHW per day min %d / max %d / mean %.0f'
          % (dates_tgt[s], dates_tgt[e-1], e-s, seg.reshape(e-s, -1).sum(axis=1).min(),
             seg.reshape(e-s, -1).sum(axis=1).max(), seg.reshape(e-s, -1).sum(axis=1).mean()))
np.save('cache/mhw.npy', mhw); np.save('cache/active.npy', active)
json.dump(events, open('cache/events.json', 'w'))
print('%.1f s' % (time.time()-t0))
