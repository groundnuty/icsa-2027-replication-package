import numpy as np, re, datetime as dt
z = np.load('data/climthr.npz')
res = np.load('data/results.npz')
hot, mhw, sea, tgt_doy = res['hot'], res['mhw'], z['sea'], z['tgt_doy']
N = 92

def independent_cell_events(h):
    s = ''.join('1' if x else '0' for x in h)
    runs = [(m.start(), m.end()-1) for m in re.finditer(r'1{5,}', s)]
    merged = []
    for st, en in runs:
        if merged and st - merged[-1][1] - 1 in (1, 2):
            merged[-1] = (merged[-1][0], en)
        else:
            merged.append((st, en))
    return merged

mismatch = 0
ncells_checked = 0
for cell in range(3600):
    c, l = divmod(cell, 60)
    ev = independent_cell_events(hot[:, c, l])
    expected = np.zeros(N, bool)
    for s, e in ev:
        expected[s:e+1] = True
    got = mhw[:, c, l].astype(bool)
    if not np.array_equal(expected, got):
        mismatch += 1
        if mismatch <= 3:
            print('MISMATCH cell', c, l, 'expected', ev, 'got days', np.where(got)[0])
    if sea[c, l]: ncells_checked += 1
print('mismatches:', mismatch, 'sea cells checked:', ncells_checked)

# verify active + events
active = mhw.astype(bool).any(axis=(1,2))
events, i = [], 0
while i < N:
    if active[i]:
        j = i
        while j+1 < N and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else: i += 1
dates = [dt.date(2009,6,1) + dt.timedelta(days=k) for k in range(N)]
print('events:', [(dates[s].isoformat(), dates[e].isoformat(), e-s+1) for s, e in events])
# per-day active vs manual: days with any cell in MHW
print('active days:', [dates[i].isoformat() for i in np.where(active)[0]])
# land cells must be 0 everywhere
print('land cells all zero:', (mhw[:, ~sea.ravel()][0].shape == (0,)) or (mhw[:, ~np.repeat(sea, 1)].sum() == 0))
m = ~sea
print('land total mhw days:', int(mhw[:, m].sum()))
# max consecutive active run check: any non-active day between first and last active?
print('non-active days inside span:', [dates[i].isoformat() for i in range(events[0][0], events[-1][1]+1) if not active[i]])