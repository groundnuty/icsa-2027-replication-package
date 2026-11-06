import numpy as np, datetime as dt, json, warnings
warnings.filterwarnings('ignore')

cache = '/tmp/mhw_cache'
cube = np.load(f'{cache}/cube.npy')
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
nb = 4028
tgt = cube[nb:].astype('float64')
dates_t = dates[nb:]
thresh_s = np.load(f'{cache}/thresh_s.npy')
clim_s = np.load(f'{cache}/clim_s.npy')

sea = np.isfinite(tgt).all(axis=0)
print('sea cells:', int(sea.sum()), '| land cells:', int((~sea).sum()))

def doy(dd):
    leap = dd.year % 4 == 0 and (dd.year % 100 != 0 or dd.year % 400 == 0)
    tt = dd.timetuple().tm_yday
    return tt + 1 if (not leap and dd.month > 2) else tt

tdoys = np.array([doy(d) for d in dates_t])
th = thresh_s[tdoys].reshape(len(tdoys), 60, 60)
hot = np.greater_equal(tgt, th, where=np.isfinite(tgt), out=np.zeros(tgt.shape, dtype=bool))
print('hot cell-days:', int(hot.sum()), '| hot fraction over sea:', round(float(hot[:, sea].mean()), 4))

def runs_of_true(v):
    out = []; n = len(v); i = 0
    while i < n:
        if v[i]:
            j = i
            while j + 1 < n and v[j+1]:
                j += 1
            out.append((i, j)); i = j + 1
        else:
            i += 1
    return out

mhw = np.zeros(tgt.shape, dtype='uint8')
n_runs5 = n_joined = per_cell_events = 0
for r in range(60):
    for c in range(60):
        if not sea[r, c]:
            continue
        rs = runs_of_true(hot[:, r, c])
        rs5 = [(s, e) for (s, e) in rs if e - s + 1 >= 5]
        n_runs5 += len(rs5)
        if not rs5:
            continue
        merged = [list(rs5[0])]
        for (s, e) in rs5[1:]:
            gap = s - merged[-1][1] - 1
            if gap <= 2:
                merged[-1][1] = e; n_joined += 1
            else:
                merged.append([s, e])
        per_cell_events += len(merged)
        for (s, e) in merged:
            mhw[s:e+1, r, c] = 1

print('hot runs >=5 (pre-join):', n_runs5)
print('joins performed:', n_joined)
print('per-cell MHWs (post-join):', per_cell_events)
print('MHW cell-days:', int(mhw.sum()))
np.save(f'{cache}/mhw.npy', mhw)
np.save(f'{cache}/sea.npy', sea)

active = mhw.reshape(len(tdoys), -1).any(axis=1)
print('active days:', int(active.sum()), 'of', len(active))
evs = runs_of_true(active)
events = [{'onset': dates_t[s].isoformat(), 'end': dates_t[e].isoformat()} for (s, e) in evs]
print('regional events:')
for ev in events:
    dur = (dt.date.fromisoformat(ev['end']) - dt.date.fromisoformat(ev['onset'])).days + 1
    print('  ', ev['onset'], '->', ev['end'], f'({dur} days)')
active_sea = mhw.reshape(len(tdoys), 60, 60)[:, sea].any(axis=1)
print('active == active over sea cells only?', bool((active == active_sea).all()))
with open(f'{cache}/events.json','w') as f:
    json.dump(events, f, indent=1)
t_idx, r, c = np.unravel_index(np.argmax(np.where(mhw > 0, tgt, -np.inf)), tgt.shape)
print('hottest MHW cell-day:', dates_t[int(t_idx)], (int(r), int(c)),
      'SST', round(float(tgt[t_idx,r,c]),3), 'K, thresh', round(float(th[t_idx,r,c]),3),
      'K, clim', round(float(clim_s[tdoys[t_idx], r*60+c]),3),
      'K, anom', round(float(tgt[t_idx,r,c]-clim_s[tdoys[t_idx], r*60+c]),3), 'K')