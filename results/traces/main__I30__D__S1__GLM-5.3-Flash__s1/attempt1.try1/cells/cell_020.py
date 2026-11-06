import numpy as np, datetime as dt, json

base_sst = np.load('/work/base_sst.npy'); targ_sst = np.load('/work/targ_sst.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy'); sea = np.load('/work/sea.npy')
START = dt.date(1991,12,27)

def doy_map(d):
    y = d.timetuple().tm_yday
    if not (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)) and d.month >= 3:
        return y + 1
    return y

targ_dates = [START + dt.timedelta(days=int(x)) for x in np.arange(6792, 6884)]  # placeholder; recompute below
# recompute properly from saved arrays' known ranges
base_dates = [dt.date(1991,12,27) + dt.timedelta(days=i) for i in range(base_sst.shape[0])]
targ_dates = [dt.date(2010,6,1) + dt.timedelta(days=i) for i in range(targ_sst.shape[0])]
assert targ_dates[0]==dt.date(2010,6,1) and targ_dates[-1]==dt.date(2010,8,31)

doy_t = np.array([doy_map(d) for d in targ_dates]) - 1
thr_t = thr_s[doy_t]                       # (92,60,60) float64
with np.errstate(invalid='ignore'):
    hot = targ_sst >= thr_t                # NaN >= x -> False
hot[~np.isfinite(targ_sst)] = False        # land/missing never hot
print('hot days total:', hot.sum(), 'per-day active-any-cell range:', hot.any(axis=(1,2)).sum())

nt = targ_sst.shape[0]
mhw = np.zeros((nt, 60, 60), dtype=np.uint8)
n_mhw_per_cell = 0
for i in range(60):
    for j in range(60):
        if not sea[i, j]:
            continue
        h = hot[:, i, j]
        idx = np.flatnonzero(h)
        if idx.size == 0:
            continue
        splits = np.flatnonzero(np.diff(idx) > 1)
        starts = np.r_[idx[0], idx[splits + 1]]
        ends   = np.r_[idx[splits], idx[-1]]
        keep = (ends - starts + 1) >= 5
        s, e = starts[keep], ends[keep]
        if s.size == 0:
            continue
        ms, me = [s[0]], [e[0]]
        for k in range(1, s.size):
            if s[k] - me[-1] - 1 <= 2:
                me[-1] = e[k]
            else:
                ms.append(s[k]); me.append(e[k])
        n_mhw_per_cell += len(ms)
        for a, b in zip(ms, me):
            mhw[a:b+1, i, j] = 1

active = mhw.any(axis=(1, 2)).astype(bool)
print('per-cell MHWs total:', n_mhw_per_cell)
print('active days:', active.sum(), 'of', nt)

# regional events: maximal runs of consecutive active days
events = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j + 1 < nt and active[j + 1]:
            j += 1
        events.append((targ_dates[i], targ_dates[j]))
        i = j + 1
    else:
        i += 1
print('n regional events:', len(events))
for a, b in events:
    print('  ', a, '->', b, f'({(b-a).days+1} d)')

np.save('/work/mhw.npy', mhw); np.save('/work/hot.npy', hot); np.save('/work/active.npy', active)
