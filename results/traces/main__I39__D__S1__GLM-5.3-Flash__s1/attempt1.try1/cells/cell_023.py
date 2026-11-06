import numpy as np, datetime as dt

coords = np.load('/work/coords.npz', allow_pickle=True)
time_tgt = coords['time_tgt']
mhw = np.load('/work/mhw.npy')          # (92,60,60) uint8
sea = np.load('/work/sea.npy')          # (60,60) bool

# active: at least one SEA cell inside a per-cell MHW that day
mhw_sea = mhw * sea[None, :, :].astype(np.uint8)
active = mhw_sea.reshape(mhw_sea.shape[0], -1).max(axis=1).astype(bool)
print('active days:', int(active.sum()), 'of', len(active))

# regional events: maximal runs of consecutive active days (no gap joining)
events = []
j = 0; n = len(active)
while j < n:
    if active[j]:
        e = j
        while e+1 < n and active[e+1]: e += 1
        events.append((j, e))
        j = e + 1
    else:
        j += 1
print('num regional events:', len(events))
for s, e in events:
    d0 = np.datetime64(time_tgt[s], 'D'); d1 = np.datetime64(time_tgt[e], 'D')
    print('event: %s .. %s  (%d days)' % (d0, d1, e-s+1))

# save events
np.save('/work/events_idx.npy', np.array(events, dtype=int))

# quick stats per event: max cells in MHW, active cell count series
for s, e in events:
    cnt = mhw_sea[s:e+1].reshape(e-s+1, -1).sum(axis=1)
    print('event %s..%s: active-cell count min/mean/max = %d/%.1f/%d' % (
        np.datetime64(time_tgt[s],'D'), np.datetime64(time_tgt[e],'D'), cnt.min(), cnt.mean(), cnt.max()))
