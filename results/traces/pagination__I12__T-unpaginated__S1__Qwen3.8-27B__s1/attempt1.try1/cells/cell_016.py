import numpy as np, pickle, datetime as dt

t = np.load('/tmp/tgt.npz'); tgt = t['arr']; tdates = [s for s in t['dates']]; ttimes = t['times']
thr_sm = np.load('/tmp/thr_sm.npy')
meta = pickle.load(open('/tmp/region_meta.pkl','rb'))

# verify doy60 identity on sea cells
clim_raw = np.load('/tmp/clim_raw.npy'); thr_raw = np.load('/tmp/thr_raw.npy')
finite_tgt = np.all(np.isfinite(tgt), axis=0).reshape(3600)
sea = np.where(finite_tgt)[0]
print('doy60 identity (sea): thr', bool(np.allclose(thr_raw[59,sea], 0.5*(thr_raw[58,sea]+thr_raw[60,sea]))),
      'clim', bool(np.allclose(clim_raw[59,sea], 0.5*(clim_raw[58,sea]+clim_raw[60,sea]))))

# doy mapping
doy_of_md = {}
d = dt.date(2000,1,1)
while d.year == 2000:
    doy_of_md[(d.month, d.day)] = d.timetuple().tm_yday
    d += dt.timedelta(days=1)
doy = lambda date: doy_of_md[(date.month, date.day)]
td = [dt.date.fromisoformat(s) for s in tdates]
doy_tgt = np.array([doy(x) for x in td])
print('target doy range:', doy_tgt.min(), doy_tgt.max())

tgt_flat = tgt.reshape(92, 3600)
hot = tgt_flat >= thr_sm[doy_tgt]        # (92, 3600), land False (NaN compare)
print('hot days total (sea):', int(hot[:, sea].sum()), 'hot cell-days max per cell:', int(hot[:, sea].max(axis=0).max()))

mask = np.zeros((92, 3600), dtype=bool)
n_mhw_per_cell = np.zeros(3600, dtype=int)
for c in range(3600):
    h = hot[:, c]
    if not h.any():
        continue
    pad = np.concatenate(([False], h, [False]))
    dd = np.diff(pad.astype(np.int8))
    s = np.where(dd == 1)[0]
    e = np.where(dd == -1)[0] - 1
    ok = (e - s + 1) >= 5
    s, e = s[ok].astype(int), e[ok].astype(int)
    if s.size == 0:
        continue
    js, je = [s[0]], [e[0]]
    for i in range(1, s.size):
        if s[i] - je[-1] - 1 <= 2:      # gap of 1 or 2 non-hot days -> join
            je[-1] = e[i]
        else:
            js.append(s[i]); je.append(e[i])
    n_mhw_per_cell[c] = len(js)
    m = mask[:, c]
    for a_, b_ in zip(js, je):
        m[a_:b_+1] = True

print('cells with >=1 MHW:', int((n_mhw_per_cell>0).sum()), '| land cells with MHW:', int(n_mhw_per_cell[~finite_tgt].sum()))
mask3 = mask.reshape(92, 60, 60)
active = mask3.any(axis=(1,2))
print('active days:', int(active.sum()), 'of 92')
# events
ev = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]:
            j += 1
        ev.append((tdates[i], tdates[j]))
        i = j+1
    else:
        i += 1
for e_ in ev:
    print('EVENT:', e_[0], '->', e_[1], f'({(dt.date.fromisoformat(e_[1])-dt.date.fromisoformat(e_[0])).days+1} days)')
np.save('/tmp/mhw_mask.npy', mask)
import json
json.dump({'events': ev, 'n_active': int(active.sum())}, open('/tmp/events_tmp.json','w'))