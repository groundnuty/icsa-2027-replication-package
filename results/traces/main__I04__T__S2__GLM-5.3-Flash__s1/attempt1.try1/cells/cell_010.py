import numpy as np, os, json, xarray as xr, pandas as pd, time as tm

tgt = np.load('/tmp/tgt.npy')                # (92,60,60) float64
sea2d = np.load('/tmp/finite_all_t.npy')
thr_s = np.load('/tmp/thr_sm.npy')           # (366, nsea)
clim_s = np.load('/tmp/clim_sm.npy')
dates = np.load('/tmp/dates.npy')
tgt_dates = dates[14031:14123]
nsea = int(sea2d.sum()); sea_flat = np.flatnonzero(sea2d.ravel())

# leap-calendar DOY (1..366) for each target date
pd_dates = pd.to_datetime(tgt_dates)
doy1 = pd_dates.map(lambda ts: (ts.replace(day=1, month=1) + pd.Timedelta(days=int(ts.strftime('%j'))-1)).timetuple().tm_yday)
# simpler: dayofyear is already leap-based
doy1 = pd_dates.dayofyear.values.astype(int)
doy0 = doy1 - 1
print('target DOY range:', doy1[0], '..', doy1[-1], '(unique count', len(np.unique(doy1)), ')')

tgf = tgt.reshape(92, -1)[:, sea_flat]                      # (92, nsea)
hot = tgf >= thr_s[doy0, :]                                 # (92, nsea) bool
print('hot days total:', int(hot.sum()), 'of', 92*nsea, '(%0.2f%%)' % (100*hot.mean()))
print('hot days per cell: min %d max %d mean %.1f' % (hot.sum(0).min(), hot.sum(0).max(), hot.sum(0).mean()))

# per-cell MHWs: runs >=5 hot, join gaps <=2, over target period only
def mhw_series(hotv):
    n = len(hotv)
    runs = []  # (start, end) inclusive, hot runs
    i = 0
    while i < n:
        if hotv[i]:
            j = i
            while j+1 < n and hotv[j+1]: j += 1
            runs.append([i, j]); i = j+1
        else:
            i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    # join gaps <=2
    if not runs: return np.zeros(n, bool), 0
    merged = [runs[0]]
    for s, e in runs[1:]:
        if s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    out = np.zeros(n, bool)
    for s, e in merged: out[s:e+1] = True
    return out, len(merged)

mhw = np.zeros((92, nsea), bool)
n_mhw_cells = []
for c in range(nsea):
    mhw[:, c], k = mhw_series(hot[:, c])
    n_mhw_cells.append(k)
n_mhw_cells = np.array(n_mhw_cells)
print('cells with >=1 per-cell MHW:', int((n_mhw_cells > 0).sum()), 'of', nsea,
      '| total per-cell MHWs:', int(n_mhw_cells.sum()), '| max per cell:', int(n_mhw_cells.max()))
print('MHW mask days total:', int(mhw.sum()))

# regional active days and events
active = mhw.any(axis=1)
print('active days:', int(active.sum()), 'of 92')
events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else:
        i += 1
print('regional events:', len(events))
for s, e in events:
    print('  ', str(tgt_dates[s]), '->', str(tgt_dates[e]), '(len %d)' % (e-s+1))

# build full mask over region grid
mhw_full = np.zeros((92, 60, 60), np.uint8)
mhw_full.reshape(92, -1)[:, sea_flat] = mhw.astype(np.uint8)
np.save('/tmp/mhw_full.npy', mhw_full)
json.dump({'events': [[int(s), int(e)] for s, e in events]}, open('/tmp/events.json', 'w'))
