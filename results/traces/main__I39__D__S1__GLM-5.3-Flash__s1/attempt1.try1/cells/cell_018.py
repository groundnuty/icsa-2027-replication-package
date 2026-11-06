import numpy as np, time, datetime as dt, warnings
warnings.filterwarnings('ignore')

sst_ext = np.load('/work/sst_ext.npy'); sst_tgt = np.load('/work/sst_tgt.npy')
coords = np.load('/work/coords.npz', allow_pickle=True)
time_ext = coords['time_ext']
sst64 = sst_ext.astype(np.float64)

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def md_of_doy(d):
    i = int(np.searchsorted(cum, d, side='left') - 1)
    return i+1, d - cum[i]

ext_ord = (time_ext - np.datetime64('1970-01-01')).astype(np.int64)
ord0 = int(ext_ord[0])
def date_ord(y, m, dd):
    return int((np.datetime64('%04d-%02d-%02d' % (y, m, dd)) - np.datetime64('1970-01-01')).astype(np.int64))

# build day -> row map and pools, with brute-force cross-check on sample days
pool_idx = np.full((365, 121), -1, dtype=np.int64)
row_of_day = {}
k = 0
for d in range(1, 367):
    if d == 60: continue
    row_of_day[d] = k
    m, dd = md_of_doy(d)
    parts = []
    for y in range(1992, 2003):
        c = date_ord(y, m, dd)
        parts.append(np.arange(c-5-ord0, c+5-ord0+1))
    pool_idx[k] = np.concatenate(parts)
    k += 1
assert k == 365 and len(row_of_day) == 365
assert row_of_day[1] == 0 and row_of_day[59] == 58 and row_of_day[61] == 59 and row_of_day[366] == 364

# brute-force check for a few days: pool = all ext dates within +-5 days of a baseline date with same (m,dd)
def brute_pool(d):
    m, dd = md_of_doy(d)
    base = set()
    for y in range(1992, 2003):
        c = dt.date(y, m, dd)
        for off in range(-5, 6):
            base.add(c + dt.timedelta(days=off))
    mask = np.array([dt.date(1970,1,1) + dt.timedelta(days=int(o)) for o in ext_ord]) if False else None
    # faster: convert ext_ord to dates
    dates = np.array([dt.date(1970,1,1) + dt.timedelta(days=int(o)) for o in ext_ord])
    sel = np.array([x in base for x in dates])
    return np.flatnonzero(sel)

for d in [1, 59, 61, 153, 244, 300, 366]:
    bp = brute_pool(d)
    pp = pool_idx[row_of_day[d]]
    assert np.array_equal(np.sort(bp), np.sort(pp)), d
print('brute-force pool cross-checks OK for d in {1,59,61,153,244,300,366}')

# ---- raw threshold and climatology ----
t0 = time.time()
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = sst64[pool_idx[row_of_day[d]]]
    thr_raw[d-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clim_raw[d-1] = np.nanmean(vals, axis=0)
    if d % 90 == 0: print('d=%d done %.1fs' % (d, time.time()-t0))
print('raw loop done %.1fs' % (time.time()-t0))

thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print('day-60 fill; nan counts:', int(np.isnan(thr_raw).sum()), int(np.isnan(clim_raw).sum()))
np.save('/work/thr_raw.npy', thr_raw); np.save('/work/clim_raw.npy', clim_raw)
print('saved', thr_raw.shape)
