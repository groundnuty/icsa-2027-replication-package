import numpy as np, json, datetime as dt

data = np.load('/work/data.npy')
thr_s = np.load('/work/thr_s.npy').reshape(366,60,60)
meta = json.load(open('/work/dates.json'))
tg = [dt.date.fromisoformat(s) for s in meta['target']]
tg_data = data[4028:4120]  # (92,60,60)

cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d): return cum[d.month-1] + d.day
tg_doy = np.array([md_doy(d) for d in tg])

sea = np.isfinite(tg_data).all(axis=0)
print('sea cells:', int(sea.sum()))

thr_t = thr_s[tg_doy-1]
hot = (tg_data >= thr_t) & sea
print('hot day-cell count:', int(hot.sum()))

pad = np.zeros((94,60,60), dtype=np.int8)
pad[1:-1] = hot.astype(np.int8)
dd = np.diff(pad, axis=0)
st, sy, sx = np.nonzero(dd == 1)
en, ey, ex = np.nonzero(dd == -1)
en = en - 1
assert np.array_equal(sy*60+sx, ey*60+ex)
print('total raw runs:', len(st))

qual = (en - st + 1) >= 5
S, E, C = st[qual], en[qual], sy[qual]*60 + sx[qual]
print('runs >=5 days:', len(S))

order = np.lexsort((S, C))
S, E, C = S[order], E[order], C[order]
mhw = np.zeros((92,60,60), dtype=bool)
merged_count = 0
i, nR = 0, len(S)
cellindex = np.arange(3600).reshape(60,60)
while i < nR:
    j, ce = i, E[i]
    while j+1 < nR and C[j+1] == C[i] and S[j+1] - ce <= 3:
        j += 1
        ce = max(ce, E[j])
    mask = (C[i] == cellindex)
    mhw[S[i]:ce+1] |= mask
    merged_count += 1
    i = j+1
print('per-cell MHWs after joining:', merged_count)
print('mhw day-cell count:', int(mhw.sum()))

active = mhw.any(axis=(1,2))
print('active days:', int(active.sum()), 'of', 92)
padA = np.r_[0, active.astype(np.int8), 0]
ddA = np.diff(padA)
ev_starts = np.flatnonzero(ddA == 1)
ev_ends = np.flatnonzero(ddA == -1) - 1
events = [(str(tg[a]), str(tg[b])) for a, b in zip(ev_starts, ev_ends)]
print('regional events:', len(events))
for e in events: print(e)

np.save('/work/mhw.npy', mhw)
json.dump({'events': events, 'sea_cells': int(sea.sum())}, open('/work/events.json','w'))
print('active per-day counts:', [int(x) for x in active])
