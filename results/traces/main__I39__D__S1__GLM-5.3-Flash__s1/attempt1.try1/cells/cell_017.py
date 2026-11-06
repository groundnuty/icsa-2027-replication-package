import numpy as np, time, warnings
warnings.filterwarnings('ignore')

sst_ext = np.load('/work/sst_ext.npy'); sst_tgt = np.load('/work/sst_tgt.npy')
coords = np.load('/work/coords.npz', allow_pickle=True)
time_ext = coords['time_ext']; time_tgt = coords['time_tgt']
sst64 = sst_ext.astype(np.float64); tgt64 = sst_tgt.astype(np.float64)
sea = np.all(np.isfinite(tgt64), axis=0)
print('sea cells:', int(sea.sum()))

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def md_of_doy(d):
    i = int(np.searchsorted(cum, d, side='left') - 1)
    return i+1, d - cum[i]

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
        parts.append(np.arange(lo, hi + 1))
    pool_idx[k] = np.concatenate(parts)
    k += 1

# ---- raw threshold (90th pct, hazen) and climatology (mean) per doy d != 60 ----
t0 = time.time()
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = sst64[pool_idx[d-1]]                      # (121,60,60) copy
    thr_raw[d-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clim_raw[d-1] = np.nanmean(vals, axis=0)
    if d % 60 == 0: print('d=%d done %.1fs' % (d, time.time()-t0))
print('raw pass done %.1fs' % (time.time()-t0))

# day 60 = mean of days 59 and 61
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print('day-60 fill OK, nan count:', int(np.isnan(thr_raw).sum()), int(np.isnan(clim_raw).sum()))

np.save('/work/thr_raw.npy', thr_raw)
np.save('/work/clim_raw.npy', clim_raw)
print('saved. shape', thr_raw.shape)
