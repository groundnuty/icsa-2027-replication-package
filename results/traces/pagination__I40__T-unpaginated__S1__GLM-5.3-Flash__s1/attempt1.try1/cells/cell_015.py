import numpy as np, datetime as dt
A = np.load('analysis.npz')
hot = A['hot']; mhw = A['mhw']; sea = A['sea']
St = np.load('St.npy'); tgt_dates = np.load('tgt_dates.npy')
lat = np.load('lat.npy'); lon = np.load('lon.npy')

# --- independent per-cell implementation using python loops over runs via transitions
def cell_events(h):
    ev = []
    n = len(h); k = 0
    while k < n:
        if h[k]:
            s = k
            while k+1 < n and h[k+1]: k += 1
            ev.append([s, k])
        k += 1
    mh = [e for e in ev if e[1]-e[0]+1 >= 5]
    out = []
    for e in mh:
        if out and (e[0]-out[-1][1]-1) in (1,2):
            out[-1][1] = e[1]
        else:
            out.append(e)
    return out

mhw2 = np.zeros_like(mhw)
ncell = 0
for i in range(60):
    for j in range(60):
        for s, e in cell_events(hot[:, i, j]):
            mhw2[s:e+1, i, j] = True; ncell += 1
print('independent impl: events=%d, mask equal=%s' % (ncell, np.array_equal(mhw, mhw2)))

# union/events independent
active = mhw.any(axis=(1,2))
evs = []
k = 0
while k < 92:
    if active[k]:
        s = k
        while k+1 < 92 and active[k+1]: k += 1
        evs.append((s, k))
    k += 1
print('independent events:', [(str(tgt_dates[s])[:10], str(tgt_dates[e])[:10]) for s, e in evs])

# event 2 cells: where and what
e2 = [(t, np.argwhere(mhw[t])) for t in range(64, 70)]
cells2 = set()
for t in range(64, 70):
    for i, j in np.argwhere(mhw[t]): cells2.add((i, j))
print('event2 cells:', sorted(cells2))
for (i, j) in sorted(cells2):
    print('cell (%d,%d) lat %.2f lon %.2f SST t62..t74:' % (i, j, lat[i], lon[j]),
          np.round(St[62:75, i, j], 2))
    print('   hot flags:', hot[62:75, i, j].astype(int), ' mhw flags:', mhw[62:75, i, j].astype(int))

# event 1: is mhw == hot within event days? any hot days outside mhw runs>=5 that got excluded?
d1 = mhw[20:40].sum(axis=0)
h1 = hot[20:40].sum(axis=0)
print('event1: cells with mhw but not 5+ hot run?', np.any((d1 > 0) & (h1 < d1)))
# cells hot during event but not in mhw:
print('event1: hot&~mhw cell-days within t20..t40:', int((hot[20:40] & ~mhw[20:40]).sum()))
# which cells: they should have runs<5 (e.g. t34 50 hot cells with 1-day runs)
excl = np.argwhere(hot[34] & ~mhw[34])
print('t34 (Jul 5) hot-not-mhw cells count:', len(excl), 'sample:', excl[:5].tolist())
# their full hot pattern
if len(excl):
    i, j = excl[0]
    print('sample excl cell hot t25..t40:', hot[25:41, i, j].astype(int))
