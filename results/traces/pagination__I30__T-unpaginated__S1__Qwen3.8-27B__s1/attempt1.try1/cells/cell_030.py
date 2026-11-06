
import sys, numpy as np, datetime as dt
sys.path.insert(0,'/work/mhw')
import common

ext, tgt, done = common.load_state()
sea = np.load('/work/mhw/sea.npy')
thr_s = np.load('/work/mhw/thr_s.npy')
doy_tgt = np.load('/work/mhw/doy_tgt.npy')
mask = np.load('/work/mhw/mask.npy')
S = tgt.astype(np.float64)
thr_t = thr_s[:, doy_tgt]
hot = (S.T >= thr_t); hot[~sea, :] = False

active_cells_per_day = mask.sum(axis=1)
print('active cells per day (first 10 and around event):')
print(list(active_cells_per_day[:10]))
print(list(active_cells_per_day[25:32]))
print('max/min on event days:', active_cells_per_day[28:55].min(), active_cells_per_day[28:55].max())

# count raw runs and merges across cells
tot_runs = 0; tot_merged_into = 0
for c in range(3600):
    h = hot[c]
    runs = []
    i = 0
    while i < 92:
        if h[i]:
            j = i
            while j < 92 and h[j]: j += 1
            if j - i >= 5: runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= 2:
            merged[-1][1] = e; tot_merged_into += 1
        else:
            merged.append([s, e])
    tot_runs += len(merged)
print('total per-cell MHWs after merging:', tot_runs, '| merges applied:', tot_merged_into)

# show one example cell's pattern
c = int(np.flatnonzero(sea)[100])
pat = ''.join('H' if hot[c, t] else ('.' if not mask[c, t] else 'g') for t in range(92))
print('example cell', c, ':', pat)
tgt_dates = [dt.date(2010,6,1) + dt.timedelta(days=k) for k in range(92)]
print('   dates:', tgt_dates[0], '...')
# verify: any non-hot day inside mask must be a gap day (bridged)
for c in range(0, 3600, 97):
    bad = (mask[c] & ~hot[c])
    for t in np.flatnonzero(bad):
        # gap day: must have hot on both sides within 2
        ok = (t > 0 and t < 91 and hot[c, t-1] and (hot[c, t+1] or (t+1 < 92 and hot[c, t+1])))
        # simpler: check run structure directly
        pass
# rigorous check: recompute mask with an independent implementation (vectorized labeling)
def cell_mhw_v2(h):
    n = len(h)
    # extend with sentinels
    h2 = np.concatenate(([False], h, [False]))
    rise = np.flatnonzero(~h2[:-1] & h2[1:])      # hot run starts (in h2 coords)
    fall = np.flatnonzero(h2[:-1] & ~h2[1:])      # hot run ends (exclusive, h2 coords)
    runs = [(s-1, e-1) for s, e in zip(rise, fall) if e - s >= 5]  # back to h coords, length>=5
    out = np.zeros(n, bool)
    for s, e in runs:
        out[s:e] = True
    return out
mismatch = 0
for c in range(3600):
    if cell_mhw_v2(hot[c]).any() != mask[c].any() or not np.array_equal(cell_mhw_v2(hot[c]), mask[c]):
        mismatch += 1
print('mismatches vs independent implementation:', mismatch)
