import numpy as np, datetime as dt, calendar, json

S64 = np.load('/tmp/mhw/S32.npy').astype(np.float64)
dates = [dt.date.fromisoformat(str(s)) for s in np.load('/tmp/mhw/dates.npy')]
n_base_ext = 4028
thr_sm = np.load('/tmp/mhw/thr_sm.npy')   # (366, 3600)

def mapped_doy(d):
    if d.month==2 and d.day==29: return 60
    yday = d.timetuple().tm_yday
    return yday if calendar.isleap(d.year) else (yday if yday<=59 else yday+1)

tgt_dates = dates[n_base_ext:]
assert len(tgt_dates)==92
doys = np.array([mapped_doy(d) for d in tgt_dates])
print('target doy range', doys[0], doys[-1], 'strictly increasing:', bool((np.diff(doys)==1).all()))

tgt = S64[n_base_ext:]
finite_all = np.isfinite(tgt).all(axis=0)     # (60,60) sea cells
sea_flat = finite_all.reshape(3600)
flat = tgt.reshape(92, 3600)
thr_sel = thr_sm[doys-1]                      # (92,3600)

hot = np.zeros((92,3600), dtype=bool)
with np.errstate(invalid='ignore'):
    hot[:, sea_flat] = flat[:, sea_flat] >= thr_sel[:, sea_flat]
print('hot day-cells:', int(hot.sum()), '| hot days per sea cell: min/mean/max =',
      int(hot[:,sea_flat].sum(axis=0).min()), round(float(hot[:,sea_flat].mean()),2), int(hot[:,sea_flat].sum(axis=0).max()))
print('NaN thresholds at sea cells:', bool(np.isnan(thr_sel[:, sea_flat]).any()))

mhw_in = np.zeros((92,3600), dtype=bool)
n_runs5 = 0; n_joined = 0; n_final = 0
for c in range(3600):
    if not sea_flat[c]: continue
    h = hot[:,c]
    if not h.any(): continue
    idx = np.flatnonzero(h)
    runs = []
    s = idx[0]; prev = idx[0]
    for k in idx[1:]:
        if k == prev+1: prev = k
        else: runs.append((s,prev)); s=k; prev=k
    runs.append((s,prev))
    runs5 = [(a,b) for a,b in runs if b-a+1>=5]
    n_runs5 += len(runs5)
    if not runs5: continue
    merged = []
    cs, ce = runs5[0]
    for a,b in runs5[1:]:
        if a - ce - 1 <= 2:
            ce = b; n_joined += 1
        else:
            merged.append((cs,ce)); cs,ce = a,b
    merged.append((cs,ce))
    n_final += len(merged)
    for a,b in merged:
        mhw_in[a:b+1, c] = True

print('runs >=5d:', n_runs5, '| joins:', n_joined, '| final per-cell MHWs:', n_final)

active = mhw_in.any(axis=1)
print('active days:', int(active.sum()), 'of 92')
idx = np.flatnonzero(active)
events = []
if idx.size:
    s=idx[0]; prev=idx[0]
    for k in idx[1:]:
        if k==prev+1: prev=k
        else: events.append((s,prev)); s=k; prev=k
    events.append((s,prev))
ev = [(tgt_dates[a].isoformat(), tgt_dates[b].isoformat(), int(b-a+1)) for a,b in events]
print('regional events (onset, end, days):')
for e in ev: print('  ', e)

mask = mhw_in.reshape(92,60,60).astype(np.uint8)
mask[:, ~finite_all] = 0
np.save('/tmp/mhw/mask.npy', mask)
with open('/tmp/mhw/events.json','w') as f:
    json.dump(ev, f)
print('saved mask', mask.shape, mask.dtype, 'sum', int(mask.sum()))
print('mask nonzero on non-sea cells:', int(mask[:, ~finite_all].sum()))
