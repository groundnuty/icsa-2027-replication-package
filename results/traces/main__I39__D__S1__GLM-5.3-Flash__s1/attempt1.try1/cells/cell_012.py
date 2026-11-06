import numpy as np, time

sst_ext = np.load('/work/sst_ext.npy'); sst_tgt = np.load('/work/sst_tgt.npy')
coords = np.load('/work/coords.npz', allow_pickle=True)
time_ext = coords['time_ext']; time_tgt = coords['time_tgt']
sst64 = sst_ext.astype(np.float64); tgt64 = sst_tgt.astype(np.float64)
sea = np.all(np.isfinite(tgt64), axis=0)

# correct cumulative days BEFORE month m (non-leap), Feb counted with 28
cum = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
def md_of_doy(d):
    i = int(np.searchsorted(cum, d, side='right') - 1)
    return i+1, d - cum[i]
for d, exp in [(1,(1,1)),(59,(2,28)),(60,None),(61,(3,1)),(151,(5,31)),(152,(6,1)),(243,(8,31)),(334,(11,30)),(365,(12,31)),(366,(12,31))]:
    if exp: assert md_of_doy(d) == exp, (d, md_of_doy(d))
print('md_of_doy OK: Jun1 doy=%d, Aug31 doy=%d, Dec31 doy=%d' % (md_of_doy(152)[0], 243, 366))

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
    assert len(pi) == 121 and len(np.unique(pi)) == 121
    pool_idx[k] = pi
    k += 1
assert k == 365
print('pool_idx built:', pool_idx.shape)

nan_per_day = (~np.isfinite(sst64)).sum(axis=(1,2))
print('ext days with any NaN in region:', int((nan_per_day>0).sum()), '; max NaNs/day:', int(nan_per_day.max()))

t0 = time.time()
vals = sst64[pool_idx[0]]
q = np.nanquantile(vals, 0.9, axis=0, method='hazen')
print('one nanquantile call: %.3f s' % (time.time()-t0), 'shape', q.shape)
