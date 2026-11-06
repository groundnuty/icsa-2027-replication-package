import os, numpy as np, xarray as xr, json, time as _t

t0 = _t.time()
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

L0, L1, O0, O1 = 545, 604, 721, 780  # inclusive region indices

# --- extract target slice: 92 days 2019-06-01..2019-08-31 ---
sst_t = ds['analysed_sst'].isel(time=slice(13665, 13757),
                                latitude=slice(L0, L1+1),
                                longitude=slice(O0, O1+1)).values.astype(np.float64)
print('target extracted', sst_t.shape, 't=%.1fs' % (_t.time()-t0))

# --- extract extended baseline 1991-12-27 .. 2003-01-05 ---
sst_b = ds['analysed_sst'].isel(time=slice(3647, 7675),
                                latitude=slice(L0, L1+1),
                                longitude=slice(O0, O1+1)).values.astype(np.float64)
np.save('/work/sst_b.npy', sst_b)
print('baseline extracted', sst_b.shape, 't=%.1fs' % (_t.time()-t0))

# baseline day-of-year mapping (month/day, 1..366)
bd = np.arange('1991-12-27', '2003-01-06', dtype='datetime64[D]')
bmonths = bd.astype('datetime64[M]').astype(int) % 12 + 1
bdays = (bd - bd.astype('datetime64[M]')).astype(int) + 1
bleap = (bmonths == 2) & (bdays == 29)
bdoy = np.where(bmonths <= 2, bdays, bdays + 2 + (bmonths == 2))
def is_leap(y):
    return (y % 4 == 0) and ((y % 100 != 0) or (y % 400 == 0))
yrs = bd.astype('datetime64[Y]').astype(int) + 1970
bdoy = np.where(bmonths > 2, bdays + 59 + is_leap(yrs).astype(int), bdoy)
assert bdoy.min() >= 1 and bdoy.max() <= 366
print('baseline doy range', bdoy.min(), bdoy.max(), '| unique doys present:', len(np.unique(bdoy)))
print('day-60 baseline values:', np.sum(bdoy == 60))

# 366-day offsets: window offsets o in -5..5 such that doy(d+o) == target doy (d!=60), valid within extended range
per_target = {}
for tgt in range(1, 367):
    if tgt == 60:
        continue
    offs = []
    for o in range(-5, 6):
        nd = bd + np.timedelta64(o, 'D')
        sel = (bdoy == tgt)
        cand = np.flatnonzero(sel & (nd >= bd[0]) & (nd <= bd[-1]))
        for idx in cand:
            offs.append(idx + o)  # absolute day offset from extended start
    per_target[tgt] = np.asarray(sorted(offs), dtype=np.int64)
print('pool offsets built; sizes min/max:', min(len(v) for v in per_target.values()),
      max(len(v) for v in per_target.values()), 't=%.1fs' % (_t.time()-t0))

NT, NY, NX = sst_b.shape
thr = np.full((366, NY, NX), np.nan, dtype=np.float64)
clm = np.full((366, NY, NX), np.nan, dtype=np.float64)
sst_f = sst_b.reshape(NT, -1)
fin = np.isfinite(sst_f)

for tgt in range(1, 367):
    if tgt == 60:
        continue
    offs = per_target[tgt]
    pool = sst_f[offs]                      # (P, NY*NX), float64
    pool_f = pool[fin[offs]]                # drop rows that are fully NaN (no cell is fully NaN)
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

# day 60 = mean of day 59 and 61
thr[59] = 0.5 * (thr[58] + thr[59+1] if False else thr[60])
clm[59] = 0.5 * (clm[58] + clm[60])

# circular 31-day centred moving mean (day d averages d-15..d+15 mod 366)
padded_t = np.concatenate([thr[335:], thr, thr[:15]], axis=0)
padded_c = np.concatenate([clm[335:], clm, clm[:15]], axis=0)
thr_s = padded_t.cumsum(axis=0)
thr_s[31:] = thr_s[31:] - thr_s[:-31]
thr_smooth = thr_s / 31.0
clm_s = padded_c.cumsum(axis=0)
clm_s[31:] = clm_s[31:] - clm_s[:-31]
clm_smooth = clm_s / 31.0
print('smoothing done t=%.1fs' % (_t.time()-t0))

np.save('/work/thr_s.npy', thr_smooth)
np.save('/work/clm_s.npy', clm_smooth)
print('ALL DONE t=%.1fs' % (_t.time()-t0))
