
import sys, numpy as np, datetime as dt
sys.path.insert(0,'/work/mhw')
import common

ext, tgt, done = common.load_state()
sea = np.load('/work/mhw/sea.npy')
thr_s = np.load('/work/mhw/thr_s.npy')
doy_tgt = np.load('/work/mhw/doy_tgt.npy')

S = tgt.astype(np.float64)  # (92, 3600)
thr_t = thr_s[:, doy_tgt]          # (3600, 92)
hot = S.T >= thr_t                 # (3600, 92)
hot[~sea, :] = False
print('hot day-cell count:', int(hot.sum()))

def cell_mhw(h):
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]:
                j += 1
            if j - i >= 5:
                runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    m = np.zeros(n, bool)
    for s, e in merged:
        m[s:e] = True
    return m

mask = np.zeros((92, 3600), bool)
n_mhw_cells = 0
for c in range(3600):
    if not sea[c]:
        continue
    m = cell_mhw(hot[c])
    if m.any():
        n_mhw_cells += 1
    mask[:, c] = m
print('cells inside >=1 per-cell MHW:', n_mhw_cells)

active = mask.any(axis=1)
print('active days:', int(active.sum()), 'of 92')
events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j < 92 and active[j]:
            j += 1
        events.append((i, j - 1))
        i = j
    else:
        i += 1
tgt_dates = [dt.date(2010,6,1) + dt.timedelta(days=k) for k in range(92)]
print('events:')
for s, e in events:
    print('  ', tgt_dates[s].isoformat(), '->', tgt_dates[e].isoformat(), 'len', e - s + 1)
np.save('/work/mhw/mask.npy', mask)
np.save('/work/mhw/active.npy', active)
with open('/work/mhw/events.pkl','wb') as f:
    import pickle; pickle.dump([(tgt_dates[s].isoformat(), tgt_dates[e].isoformat()) for s, e in events], f)
print('saved')
