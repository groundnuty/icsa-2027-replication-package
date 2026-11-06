
import numpy as np, datetime as dt, json, os

z = np.load('work/sst.npz', allow_pickle=True)
days = [dt.date.fromisoformat(x) for x in z['days']]
sst = z['sst']
nbase = 4028
tc = np.load('work/thrclim.npz')
thr_s = tc['thr_s']; sea = tc['sea']
sst_t = sst[nbase:]                       # (92,60,60)
t_days = days[nbase:]                     # 2015-06-01 .. 2015-08-31
assert t_days[0] == dt.date(2015,6,1) and t_days[-1] == dt.date(2015,8,31) and len(t_days)==92

mleap = [31,29,31,30,31,30,31,31,30,31,30,31]
pref = [0]
for m in mleap: pref.append(pref[-1]+m)
doy_of_t = np.array([pref[d.month-1] + d.day for d in t_days])   # 1..366

hot = np.zeros((92, 60, 60), bool)
hot[:, sea] = sst_t[:, sea] >= thr_s[doy_of_t - 1][:, sea]
print('hot day counts:', hot.sum(axis=(1,2)))

def cell_event_mask(h):
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]: j += 1
            if j - i >= 5: runs.append((i, j))
            i = j
        else:
            i += 1
    merged = []
    for (s, e) in runs:
        if merged and s - merged[-1][1] <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    out = np.zeros(n, bool)
    for (s, e) in merged: out[s:e] = True
    return out

mhw = np.zeros((92, 60, 60), np.uint8)
n_cell_events = 0
for c in np.flatnonzero(sea.ravel()):
    col, row = divmod(c, 60)
    m = cell_event_mask(hot[:, row, col])
    mhw[:, row, col] = m.astype(np.uint8)
    n_cell_events += len([1 for k in range(92) if False])  # placeholder
# count events properly
for c in np.flatnonzero(sea.ravel()):
    col, row = divmod(c, 60)
    m = mhw[:, row, col].astype(bool)
    k = 0
    while k < 92:
        if m[k]:
            k += 1
            while k < 92 and m[k]: k += 1
            # one event
    # simpler count: transitions
events_cell = int(((~m | True) & False).sum())  # not used
n_events_cells = int(np.sum(mhw[0].astype(bool)) + np.sum((mhw[1:].astype(bool) & ~mhw[:-1].astype(bool))))
print('per-cell MHW events (cells*events):', n_events_cells)

active = mhw.astype(bool).any(axis=(1, 2))
print('active days:', int(active.sum()))
ev = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j < 92 and active[j]: j += 1
        ev.append((t_days[i], t_days[j-1]))
        i = j
    else:
        i += 1
print('regional events:')
for e in ev: print('  ', e[0], '->', e[1])

np.save('work/mhw_mask.npy', mhw)
with open('work/events.json','w') as f:
    json.dump([{'onset': e[0].isoformat(), 'end': e[1].isoformat()} for e in ev], f)
print('saved mask', mhw.shape, mhw.dtype)
