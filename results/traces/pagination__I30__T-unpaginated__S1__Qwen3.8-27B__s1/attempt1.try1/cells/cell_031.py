
import sys, numpy as np, datetime as dt
sys.path.insert(0,'/work/mhw')
sea = np.load('/work/mhw/sea.npy')
thr_s = np.load('/work/mhw/thr_s.npy')
doy_tgt = np.load('/work/mhw/doy_tgt.npy')
mask = np.load('/work/mhw/mask.npy')
import common
ext, tgt, done = common.load_state()
S = tgt.astype(np.float64)
hot = (S.T >= thr_s[:, doy_tgt]); hot[~sea, :] = False   # (3600, 92)

def cell_mhw_v2(h):
    n = len(h)
    h2 = np.concatenate(([False], h, [False]))
    rise = np.flatnonzero(~h2[:-1] & h2[1:])
    fall = np.flatnonzero(h2[:-1] & ~h2[1:])
    runs = [(s-1, e-1) for s, e in zip(rise, fall) if e - s >= 5]
    out = np.zeros(n, bool)
    for s, e in runs:
        out[s:e] = True
    return out

mismatch = 0
for c in range(3600):
    m2 = cell_mhw_v2(hot[c])
    if not np.array_equal(m2, mask[:, c]):
        mismatch += 1
        if mismatch <= 3:
            print('cell', c, 'orig', mask[:, c].astype(int), 'new', m2.astype(int))
print('mismatches vs independent implementation:', mismatch)

# show one example cell pattern (axes fixed)
c = int(np.flatnonzero(sea)[100])
pat = ''.join('H' if hot[c, t] else ('G' if mask[t, c] else '.') for t in range(92))
print('example cell', c, ':', pat)
tgt_dates = [dt.date(2010,6,1) + dt.timedelta(days=k) for k in range(92)]
print('June 1 = index 0; event indices 28..54 =', tgt_dates[28], '->', tgt_dates[54])
