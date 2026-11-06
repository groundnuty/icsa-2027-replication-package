import numpy as np, warnings, time

sst_ext = np.load('/work/sst_ext.npy')          # (4028,60,60) float32
sst_tgt = np.load('/work/sst_tgt.npy')          # (92,60,60) float32
coords = np.load('/work/coords.npz', allow_pickle=True)
time_ext = coords['time_ext']                   # datetime64[D]
time_tgt = coords['time_tgt']
print('ext', time_ext[0], time_ext[-1], len(time_ext), '| tgt', time_tgt[0], time_tgt[-1], len(time_tgt))

sst64 = sst_ext.astype(np.float64)
tgt64 = sst_tgt.astype(np.float64)

# Sea cells: finite SST on every target day
sea = np.all(np.isfinite(tgt64), axis=0)
print('sea cells:', int(sea.sum()), 'of', sea.size)

# day-of-year mapping 1..366 by (month, day), Feb always 29
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # days before month m (cum[m-1])
def md_of_doy(d):
    i = int(np.searchsorted(cum, d, side='right') - 1)   # cum[i] < d <= cum[i+1]
    return i+1, d - cum[i]
# checks
for d, exp in [(1,(1,1)),(59,(2,28)),(60,None),(61,(3,1)),(152,(6,1)),(243,(8,31)),(366,(12,31))]:
    if exp: assert md_of_doy(d) == exp, (d, md_of_doy(d))
print('md_of_doy checks OK; Jun1 doy =', 152+1, 'Aug31 doy =', 213+31)

# pool indices per doy d != 60 : union over y=1992..2002 of [date(y,md)-5, date(y,md)+5]
ext_ord = (time_ext - np.datetime64('1970-01-01')).astype(np.int64)
ord0 = int(ext_ord[0]); n_ext = len(ext_ord)
def date_ord(y, m, dd):
    return int((np.datetime64('%04d-%02d-%02d' % (y, m, dd)) - np.datetime64('1970-01-01')).astype(np.int64))

pool_idx = np.full((365, 121), -1, dtype=np.int64)
k = 0
for d in range(1, 367):
    if d == 60: continue
    m, dd = md_of_doy(d)
    parts = []
    for y in range(1992, 2003):
        c = date_ord(y, m, dd)
        lo, hi = c - 5 - ord0, c + 5 - ord0
        assert 0 <= lo and hi <= n_ext - 1, (d, y, lo, hi)
        parts.append(np.arange(lo, hi + 1))
    pi = np.concatenate(parts)
    assert len(pi) == 121 and len(np.unique(pi)) == 121  # windows disjoint
    pool_idx[k] = pi
    k += 1
assert k == 365
print('pool_idx built:', pool_idx.shape)

# quick NaN survey: missing baseline days inside the region
nan_per_day = (~np.isfinite(sst64)).sum(axis=(1,2))
print('ext days with any NaN in region:', int((nan_per_day>0).sum()), '; max NaNs/day:', int(nan_per_day.max()))

t0 = time.time()
vals = sst64[pool_idx[0]]
q = np.nanquantile(vals, 0.9, axis=0, method='hazen')
print('one nanquantile call: %.3f s' % (time.time()-t0))
