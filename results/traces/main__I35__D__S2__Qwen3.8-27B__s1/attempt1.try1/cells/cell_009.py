import numpy as np, pickle
d = pickle.load(open('/work/step1.pkl','rb'))
S_ext, S_tgt, doy_ext, doy_tgt, M = d['S_ext'], d['S_tgt'], d['doy_ext'], d['doy_tgt'], d['M']
t_tgt = d['t_tgt']; lat = d['lat']; lon = d['lon']
ncells = S_tgt.shape[0]*S_tgt.shape[1]
S_ext_c = S_ext.reshape(-1, S_ext.shape[0])     # (3600, 4028) days as rows
S_tgt_c = S_tgt.reshape(-1, S_tgt.shape[0])     # (3600, 92)

cols = [np.flatnonzero(M[i]) for i in range(366)]
thr = np.full((ncells, 366), np.nan)
clim = np.full((ncells, 366), np.nan)
for i in range(366):
    if i == 59:  # day 60: no pool
        continue
    X = S_ext_c[:, cols[i]]                      # (3600, 121)
    thr[:, i]  = np.nanquantile(X, 0.9, method='hazen', axis=1)
    clim[:, i] = np.nanmean(X, axis=1)
# day 60 = mean of days 59 & 61
thr[:, 59]  = 0.5*(thr[:, 58] + thr[:, 60])
clim[:, 59] = 0.5*(clim[:, 58] + clim[:, 60])
# smooth: centred 31-day circular moving mean
idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
thr_sm = thr[:, idx].mean(axis=1)
clim_sm = clim[:, idx].mean(axis=1)
print('thr_sm finite fraction:', np.isfinite(thr_sm).mean())
print('thr_sm range:', np.nanmin(thr_sm), np.nanmax(thr_sm), 'K')
print('clim_sm range:', np.nanmin(clim_sm), np.nanmax(clim_sm), 'K')
print('any NaN thr in target doy window?', np.isnan(thr_sm[:, 152:245]).any())

# sea cells: finite on every target day
sea = np.all(np.isfinite(S_tgt_c), axis=1)
print('sea cells:', int(sea.sum()), 'of', ncells)

# hot days (kelvin >= threshold)
hot = np.zeros_like(S_tgt_c, dtype=bool)
hot[sea] = S_tgt_c[sea] >= thr_sm[sea][:, doy_tgt]
print('hot day count (sea cells):', int(hot.sum()))

# per-cell MHWs: runs of >=5 hot days, merged across gaps of 1-2 non-hot days
D = 92
pad = np.zeros((ncells, D+2), dtype=bool); pad[:, 1:-1] = hot
d1 = (pad[:, 1:] & ~pad[:, :-1])   # rise at pos p (0-based in D)
d2 = (~pad[:, 1:] & pad[:, :-1])   # fall
rs, cs = np.nonzero(d1)
re, ce = np.nonzero(d2)
assert len(rs) == len(re)
runs_len = (ce + 1) - cs           # last hot day index +1 - start = length
keep = runs_len >= 5
rs, cs, ce = rs[keep], cs[keep], ce[keep]-1   # ce now last hot day
print('qualifying runs:', len(rs))
# merge per cell (already sorted by cell then start)
events = {}   # cell -> list of (start, end)
cur = None
for i in range(len(rs)):
    c, s, e = int(rs[i]), int(cs[i]), int(ce[i])
    if cur is not None and cur[0] == c and s - cur[2] - 1 <= 2:
        cur = (c, cur[1], max(cur[2], e))
    else:
        if cur is not None: events.setdefault(cur[0], []).append(cur[1:])
        cur = (c, s, e)
if cur is not None: events.setdefault(cur[0], []).append(cur[1:])
n_ev = sum(len(v) for v in events.values())
print('per-cell MHW events after merging:', n_ev, 'in', len(events), 'cells')
lens = [e - s + 1 for v in events.values() for s, e in v]
print('event lengths min/max:', min(lens), max(lens))

# mhw mask
mhw = np.zeros((ncells, D), dtype=np.uint8)
for c, v in events.items():
    for s, e in v:
        mhw[c, s:e+1] = 1
print('mhw ones:', int(mhw.sum()), 'active days:', int(mhw.sum(axis=0).astype(bool).sum()))

active = mhw.sum(axis=0) > 0
# regional events: maximal runs of active days
ev = []
in_ev = False
for i in range(D):
    if active[i] and not in_ev:
        st = i; in_ev = True
    elif not active[i] and in_ev:
        ev.append((st, i-1)); in_ev = False
if in_ev: ev.append((st, D-1))
ev_dates = [(t_tgt[s], t_tgt[e]) for s, e in ev]
print('regional events:')
for s, e in ev_dates:
    print('  ', s, '->', e, 'len', e - s + 1)

pickle.dump(dict(mhw=mhw, events=ev, sea=sea, thr_sm=thr_sm, clim_sm=clim_sm,
                 ncells=ncells), open('/work/step2.pkl','wb'))
print('saved step2')
