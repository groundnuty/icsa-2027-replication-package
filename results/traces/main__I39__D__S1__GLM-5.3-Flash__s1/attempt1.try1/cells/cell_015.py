import numpy as np, time, datetime as dt

sst_ext = np.load('/work/sst_ext.npy'); sst_tgt = np.load('/work/sst_tgt.npy')
coords = np.load('/work/coords.npz', allow_pickle=True)
time_ext = coords['time_ext']; time_tgt = coords['time_tgt']
sst64 = sst_ext.astype(np.float64); tgt64 = sst_tgt.astype(np.float64)
sea = np.all(np.isfinite(tgt64), axis=0)

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # days before month m, Feb=29 always
def md_of_doy(d):
    i = int(np.searchsorted(cum, d, side='left') - 1)
    return i+1, d - cum[i]

# cross-check the mapping against datetime for all (month, day) pairs
ok = True
for m in range(1, 13):
    for dd in range(1, 32):
        try:
            dt.date(2000, m, dd)
        except ValueError:
            continue
        d = cum[m-1] + dd
        if md_of_doy(d) != (m, dd):
            ok = False; print('MISMATCH', d, md_of_doy(d), (m,dd))
print('md_of_doy vs datetime(2000):', 'ALL OK' if ok else 'FAILED')
print('Jun 1 -> doy', cum[5]+1, '| Aug 31 -> doy', cum[7]+31, '| Dec 31 -> doy', cum[11]+31)
# target window in doy space (2010 is non-leap but mapping is by month/day)
print('target doy range: %d .. %d' % (cum[5]+1, cum[7]+31))

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
print('d=1 window:', time_ext[pool_idx[0][0]], '..', time_ext[pool_idx[0][-1]])
print('d=366 window:', time_ext[pool_idx[364][0]], '..', time_ext[pool_idx[364][-1]])

nan_per_day = (~np.isfinite(sst64)).sum(axis=(1,2))
print('ext days with any NaN in region:', int((nan_per_day>0).sum()), '; max NaNs/day:', int(nan_per_day.max()))

t0 = time.time()
vals = sst64[pool_idx[0]]
q = np.nanquantile(vals, 0.9, axis=0, method='hazen')
print('one nanquantile call: %.3f s, shape %s' % (time.time()-t0, q.shape))
