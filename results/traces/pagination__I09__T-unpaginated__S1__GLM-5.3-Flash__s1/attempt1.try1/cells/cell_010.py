import numpy as np, json, datetime as dt, os

tgt_stack = np.load('/tmp/tgt_stack.npy')      # (92, 60, 60) float64
Ts = np.load('/tmp/thr_smooth.npy')            # (366, 60, 60)
sea = np.load('/tmp/sea.npy')                  # (60, 60) bool
meta = json.load(open('/tmp/meta.json'))
tgt = [dt.date.fromisoformat(s) for s in meta['tgt']]
nt = len(tgt)

# day of year for 2022 (non-leap): 1 Jan = 1
t_doy = np.array([(d - dt.date(d.year,1,1)).days + 1 for d in tgt])
thr_t = Ts[t_doy - 1]                          # (92, 60, 60)
print('target doys:', t_doy[0], '...', t_doy[-1])

hot = tgt_stack >= thr_t                       # float64 comparison
hot[:, ~sea] = False
print('hot days total (sea cells):', int(hot.sum()), '| hot frac per day min/max:',
      hot.sum(axis=(1,2)).min(), hot.sum(axis=(1,2)).max())

mask = np.zeros_like(hot)
n_mhw_cells = 0; tot_events = 0; lens = []
for a in range(hot.shape[1]):
    for b in range(hot.shape[2]):
        if not sea[a,b]: continue
        h = hot[:, a, b]
        # run-length encode
        idx = np.flatnonzero(np.diff(np.concatenate(([0], h.view(np.int8), [0]))))
        runs = list(zip(idx[0::2], idx[1::2]))           # [start, end) pairs
        mhw_runs = [(s, e) for s, e in runs if e - s >= 5]
        if not mhw_runs: continue
        # join MHWs separated by 1 or 2 non-hot days (chain)
        merged = [list(mhw_runs[0])]
        for s, e in mhw_runs[1:]:
            gap = s - merged[-1][1]
            if 1 <= gap <= 2:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        n_mhw_cells += 1
        tot_events += len(merged)
        for s, e in merged:
            mask[s:e, a, b] = 1
            lens.append(e - s)

print('cells with >=1 MHW:', n_mhw_cells, '| per-cell MHW count:', tot_events)
print('per-cell MHW lengths: min %d max %d mean %.1f' % (min(lens), max(lens), np.mean(lens)))
active = mask.any(axis=(1,2))
print('active days:', int(active.sum()), 'of', nt)
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]: j += 1
        ev.append((tgt[i].isoformat(), tgt[j].isoformat(), j-i+1))
        i = j+1
    else:
        i += 1
print('regional events:', len(ev))
for e in ev: print('  ', e)
np.save('/tmp/mhw_mask.npy', mask)
json.dump({'events': [{'onset': a, 'end': b} for a,b,_ in ev],
           'n_mhw_cells': n_mhw_cells, 'tot_events': tot_events}, open('/tmp/ev.json','w'))
print('cwd:', os.getcwd())
