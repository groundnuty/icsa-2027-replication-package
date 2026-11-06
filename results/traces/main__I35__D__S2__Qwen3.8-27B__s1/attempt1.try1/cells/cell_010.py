import numpy as np, pickle
d = pickle.load(open('/work/step1.pkl','rb'))
S_ext, S_tgt, doy_ext, doy_tgt, M = d['S_ext'], d['S_tgt'], d['doy_ext'], d['doy_tgt'], d['M']
t_tgt = d['t_tgt']; lat = d['lat']; lon = d['lon']
S_ext_c = S_ext.reshape(-1, S_ext.shape[0])     # (3600, 4028)
S_tgt_c = S_tgt.reshape(-1, S_tgt.shape[0])     # (3600, 92)
ncells = S_tgt_c.shape[0]
assert S_ext_c.shape[0] == ncells

cols = [np.flatnonzero(M[i]) for i in range(366)]
thr = np.full((ncells, 366), np.nan)
clim = np.full((ncells, 366), np.nan)
for i in range(366):
    if i == 59:
        continue
    X = S_ext_c[:, cols[i]]
    thr[:, i]  = np.nanquantile(X, 0.9, method='hazen', axis=1)
    clim[:, i] = np.nanmean(X, axis=1)
thr[:, 59]  = 0.5*(thr[:, 58] + thr[:, 60])
clim[:, 59] = 0.5*(clim[:, 58] + clim[:, 60])
idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
thr_sm = thr[:, idx].mean(axis=1)
clim_sm = clim[:, idx].mean(axis=1)
print('thr_sm finite fraction:', round(float(np.isfinite(thr_sm).mean()), 6))
print('thr_sm range (K):', round(float(np.nanmin(thr_sm)),3), round(float(np.nanmax(thr_sm)),3))
print('clim_sm range (K):', round(float(np.nanmin(clim_sm)),3), round(float(np.nanmax(clim_sm)),3))
print('any NaN thr in target doy window?', bool(np.isnan(thr_sm[:, 152:245]).any()))

sea = np.all(np.isfinite(S_tgt_c), axis=1)
print('sea cells:', int(sea.sum()), 'of', ncells)

hot = np.zeros_like(S_tgt_c, dtype=bool)
hot[sea] = S_tgt_c[sea] >= thr_sm[sea][:, doy_tgt]
print('hot day count (sea cells):', int(hot.sum()))

D = 92
pad = np.zeros((ncells, D+2), dtype=bool); pad[:, 1:-1] = hot
rs, cs = np.nonzero(pad[:, 1:] & ~pad[:, :-1])
re, ce = np.nonzero(~pad[:, 1:] & pad[:, :-1])
assert len(rs) == len(re)
keep = (ce + 1) - cs >= 5
rs, cs, ce = rs[keep], cs[keep], ce[keep]-1
print('qualifying runs:', int(len(rs)))
events = {}
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

mhw = np.zeros((ncells, D), dtype=np.uint8)
for c, v in events.items():
    for s, e in v:
        mhw[c, s:e+1] = 1
print('mhw ones:', int(mhw.sum()), 'active days:', int((mhw.sum(axis=0) > 0).sum()))

active = mhw.sum(axis=0) > 0
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
    print('  ', s, '->', e, 'len', int(e - s + 1))
pickle.dump(dict(mhw=mhw, events=ev, sea=sea, thr_sm=thr_sm, clim_sm=clim_sm,
                 ncells=ncells, events_by_cell=events), open('/work/step2.pkl','wb'))
print('saved step2')
