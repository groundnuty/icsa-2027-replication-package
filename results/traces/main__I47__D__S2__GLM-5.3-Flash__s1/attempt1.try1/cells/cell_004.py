import os, numpy as np, xarray as xr, json, time as _t

t0 = _t.time()
sst_b = np.load('/work/sst_b.npy')
NT, NY, NX = sst_b.shape

# baseline day-of-year mapping (month/day, 1..366)
bd = np.arange('1991-12-27', '2003-01-06', dtype='datetime64[D]')
bmonths = bd.astype('datetime64[M]').astype(int) % 12 + 1
bdays = (bd - bd.astype('datetime64[M]')).astype(int) + 1
yrs = bd.astype('datetime64[Y]').astype(int) + 1970
leap = ((yrs % 4 == 0) & ((yrs % 100 != 0) | (yrs % 400 == 0))).astype(int)
bdoy = np.where(bmonths <= 2, bdays, bdays + 59 + leap)
assert bdoy.min() >= 1 and bdoy.max() <= 366
assert bdays.max() <= 31
print('baseline doy range', bdoy.min(), bdoy.max(), '| unique doys present:', len(np.unique(bdoy)),
      '| day-60 vals:', np.sum(bdoy == 60))

# pool offsets per target doy: offsets o in -5..5 with doy(day+o)==tgt, kept within extended range
per_target = {}
for tgt in range(1, 367):
    if tgt == 60:
        continue
    offs = []
    for o in range(-5, 6):
        nd = bd + np.timedelta64(o, 'D')
        cand = np.flatnonzero((bdoy == tgt) & (nd >= bd[0]) & (nd <= bd[-1]))
        for idx in cand:
            offs.append(idx + o)
    per_target[tgt] = np.asarray(sorted(offs), dtype=np.int64)
sizes = [len(v) for v in per_target.values()]
print('pool offsets built; min/median/max size:', min(sizes), int(np.median(sizes)), max(sizes),
      't=%.1fs' % (_t.time()-t0))

thr = np.full((366, NY, NX), np.nan, dtype=np.float64)
clm = np.full((366, NY, NX), np.nan, dtype=np.float64)
sst_f = sst_b.reshape(NT, -1)
fin = np.isfinite(sst_f)

for tgt in range(1, 367):
    if tgt == 60:
        continue
    offs = per_target[tgt]
    pool = sst_f[offs]
    pool_f = pool[fin[offs]]
    n = pool_f.shape[0]
    a = (n - 1) * 0.9
    lo = int(np.floor(a)); hi = int(np.ceil(a))
    part = np.sort(pool_f, axis=0)
    q = part[lo].copy()
    rem = a - lo
    if rem != 0:
        q += rem * (part[hi] - part[lo])
    thr[tgt-1] = q
    clm[tgt-1] = pool_f.mean(axis=0)
print('quantiles & means done t=%.1fs' % (_t.time()-t0))

# day 60 = mean of day 59 and day 61
thr[59] = 0.5 * (thr[58] + thr[60])
clm[59] = 0.5 * (clm[58] + clm[60])

# circular 31-day centred moving mean
padded_t = np.concatenate([thr[335:], thr, thr[:15]], axis=0)
padded_c = np.concatenate([clm[335:], clm, clm[:15]], axis=0)
s = padded_t.cumsum(axis=0); s[31:] = s[31:] - s[:-31]; thr_smooth = s / 31.0
s = padded_c.cumsum(axis=0); s[31:] = s[31:] - s[:-31]; clm_smooth = s / 31.0
print('smoothing done t=%.1fs' % (_t.time()-t0))

np.save('/work/thr_s.npy', thr_smooth)
np.save('/work/clm_s.npy', clm_smooth)
print('ALL DONE t=%.1fs' % (_t.time()-t0))
print('thr sample day180 cell(30,30): %.4f  clm: %.4f' % (thr_smooth[179,30,30], clm_smooth[179,30,30]))
