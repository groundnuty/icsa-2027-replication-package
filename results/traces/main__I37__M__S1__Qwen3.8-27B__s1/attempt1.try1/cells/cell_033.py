import time, datetime as dt, json
import numpy as np

t0 = time.time()
ext = np.load('/work/chk/ext.npy').astype(np.float64)
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in daterange(dt.date(2012,6,1), dt.date(2012,8,31))])
doy_b = doy_ext[5:5+4018]
print("doy_b head/tail:", doy_b[:5], doy_b[-5:])

# hazen sanity: type-5 (hazen) for n=10, q=0.9 -> h=(n+1)q+0.5=10 -> x_10=10
print("hazen check (expect 10.0):", np.quantile(np.arange(1,11), 0.9, method='hazen'))

finite_tgt = np.isfinite(tgt)
sea = finite_tgt.all(axis=0)
print("sea cells:", int(sea.sum()), "/", sea.size)
print("per-target-day finite fraction min/max:", finite_tgt.mean(axis=(1,2)).min(), finite_tgt.mean(axis=(1,2)).max())

CLAT, CLON = 60, 60
thr_raw = np.full((366, CLAT, CLON), np.nan)
clim_raw = np.full((366, CLAT, CLON), np.nan)
nvalid_min = np.full(366, 10**9, dtype=int)
t1 = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    js = np.where(doy_b == d)[0]
    assert len(js) == 11, (d, len(js))
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()   # 121 ext rows
    pool = ext[rows]                                                # (121,60,60)
    nv = np.isfinite(pool).sum(axis=0)
    nvalid_min[d-1] = int(nv.min())
    thr_raw[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim_raw[d-1] = np.nanmean(pool, axis=0)
print("pools done in", time.time()-t1, " min pool size:", int(nvalid_min.min()), "at doy", int(nvalid_min.argmin()+1), " max:", int(nvalid_min.max()))

# day 60 = mean of 59 and 61 (0-based idx 58, 59, 60)
thr_raw[59] = 0.5 * (thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5 * (clim_raw[58] + clim_raw[60])

def smooth31(a):
    acc = np.zeros_like(a)
    for k in range(-15, 16):
        acc += np.roll(a, -k, axis=0)
    return acc / 31.0

thr = smooth31(thr_raw)
clim = smooth31(clim_raw)

# verify smoothing by direct loop on two cells
for c in [(10, 12), (59, 0)]:
    ref = np.array([np.mean([thr_raw[(d + k) % 366, c[0], c[1]] for k in range(-15, 16)]) for d in range(366)])
    md = np.abs(thr[:, c[0], c[1]] - ref).max()
    assert md < 1e-12, md
print("smoothing verified (incl. wrap)")

print("thr range: %.4f .. %.4f K" % (np.nanmin(thr), np.nanmax(thr)))
print("clim range: %.4f .. %.4f K" % (np.nanmin(clim), np.nanmax(clim)))

np.save('/work/chk/thr.npy', thr)
np.save('/work/chk/clim.npy', clim)
np.save('/work/chk/sea.npy', sea)
json.dump({'doy_tgt': doy_tgt.tolist(), 'ext_start': str(ext_dates[0]), 'ext_end': str(ext_dates[-1])}, open('/work/chk/meta.json','w'))
print("stage done in", time.time()-t0)
