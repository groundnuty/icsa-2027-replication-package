import numpy as np, datetime as dt, json

z1 = np.load('/work/cache_stage1.npz')
z2 = np.load('/work/cache_stage2.npz')
tgt_flat = z1['tgt_sst'].reshape(92, -1)          # float64
thr_s = z2['thr_s']; tdoys = z2['tdoys']; sea = z2['sea']
nd_t, ncell = tgt_flat.shape

hot = np.zeros((nd_t, ncell), dtype=bool)
thr_t = thr_s[tdoys - 1, :]                        # (92, ncell) thresholds on target days
hot = tgt_flat >= thr_t                            # NaN >= x -> False (land never hot)
print('hot days total (sea cells): %d of %d cell-days' % (hot.sum(), nd_t*int(sea.sum())))
print('hot frac over sea: %.4f' % (hot[:, sea].mean()))

def find_runs(mask):
    """maximal True runs -> list of (start, end_exclusive)"""
    m = np.concatenate(([False], mask, [False])).astype(np.int8)
    d = np.diff(m)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return list(zip(starts.tolist(), ends.tolist()))

mhw_span = np.zeros((nd_t, ncell), dtype=bool)
n_pre = 0; n_post = 0; runs_before = []; runs_after = []
for c in range(ncell):
    if not sea[c]:
        continue
    rs = find_runs(hot[:, c])
    long_runs = [(s, e) for (s, e) in rs if (e - s) >= 5]
    n_pre += len(long_runs)
    merged = []
    for (s, e) in long_runs:
        if merged and (s - merged[-1][1]) <= 2:   # 1 or 2 non-hot days between -> join
            merged[-1][1] = e
        else:
            merged.append([s, e])
    n_post += len(merged)
    runs_before.append(len(long_runs)); runs_after.append(len(merged))
    for (s, e) in merged:
        mhw_span[s:e, c] = True

print('per-cell MHWs: before joining %d, after joining %d' % (n_pre, n_post))
print('MHW cell-days total: %d' % mhw_span.sum())

active = mhw_span.any(axis=1)
print('active days: %d of 92' % int(active.sum()))
ev_runs = find_runs(active)
t0date = dt.date(2008, 6, 1)
events = [{'onset': (t0date + dt.timedelta(days=int(s))).isoformat(),
           'end':   (t0date + dt.timedelta(days=int(e-1))).isoformat()}
          for (s, e) in ev_runs]
print('regional events: %d' % len(events))
for ev in events:
    print('  ', ev['onset'], '->', ev['end'], '(%d days)' % (
        (dt.date.fromisoformat(ev['end']) - dt.date.fromisoformat(ev['onset'])).days + 1))

# gap-joining sanity example: find a cell where joining happened
joined_cells = [c for c in range(ncell) if runs_before[c] != runs_after[c]]
print('cells with joins:', len(joined_cells))
np.savez('/work/cache_stage3.npz', mhw_span=mhw_span, active=active, hot=hot)
json.dump(events, open('/work/events.json', 'w'))
print('stage3 saved')
