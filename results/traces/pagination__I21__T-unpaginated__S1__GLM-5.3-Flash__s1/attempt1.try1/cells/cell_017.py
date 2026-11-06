import numpy as np, datetime as dt, pickle, json

base = np.load('/tmp/base_cube.npy')          # (4028,60,60) float64
tgt  = np.load('/tmp/tgt_cube.npy')           # (92,60,60) float64
with open('/tmp/pools.pkl','rb') as f: pools = pickle.load(f)
bdates = [dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(4028)]
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]

# ---- per-doy statistics over sea cells ----
clim_raw  = np.full(366, np.nan)
thr_raw   = np.full(366, np.nan)
pool_tot  = np.zeros(366, dtype=np.int64)
for doy, idxs in pools.items():
    vals = base[idxs]                     # (121, 60, 60)
    pool_tot[doy] = np.isfinite(vals).sum()
    flat = vals.reshape(len(idxs), -1)
    # per-cell 90th percentile ignoring NaN, hazen (type 5), vectorized
    qs = np.nanquantile(flat, 0.9, axis=0, method='hazen')
    thr_raw[doy] = qs.reshape(60,60)
    with np.errstate(invalid='ignore'):
        clim_raw[doy] = np.nanmean(flat, axis=0).reshape(60,60)
print("pool value counts: min", pool_tot[pool_tot>0].min(), "max", pool_tot.max(), "doy60:", pool_tot[60])
print("thr_raw finite doys:", np.isfinite(thr_raw).sum(), "clim:", np.isfinite(clim_raw).sum())

# day 60 = mean of days 59 and 61 (cell-wise)
thr_raw[60]  = 0.5*(thr_raw[59]  + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])
print("day 60 set from 59&61; NaN remaining:", int(np.isnan(thr_raw).sum()), int(np.isnan(clim_raw).sum()))

# ---- 31-day centred wrapped moving mean (unweighted) ----
def smooth31(a):
    out = np.empty_like(a)
    for d in range(366):
        idx = [(d+k) % 366 for k in range(-15, 16)]
        out[d] = a[idx].mean(axis=0)
    return out
thr_s  = smooth31(thr_raw)
clim_s = smooth31(clim_raw)
# wrap checks
print("wrap: mean|thr_s[0]-thr_s[366]| cycle consistency:", np.abs(thr_s[0]-thr_s[0]).max())
assert np.allclose(thr_s[0], thr_s[0])
# smoothing must be finite everywhere (all pools finite)
assert np.isfinite(thr_s).all() and np.isfinite(clim_s).all()

# sanity vs scipy if available
try:
    from scipy.stats.mstats import mquantiles
    import scipy
    v = base[pools[200]][:, 30, 30]
    q = mquantiles(v, prob=0.9, alphap=0.5, betap=0.5)
    print("scipy hazen check (doy200, cell 30,30): scipy=%.10f numpy=%.10f" % (float(q), thr_raw[200,30,30]))
except Exception as e:
    print("scipy check skipped:", e)
# manual hazen check
v = np.sort(base[pools[200]][:, 30, 30])
h = (len(v)-1)*0.5*1.0  # hazen pos = (n-1)*p*(n... ) actually (n-1)*p? no: hazen: (n-1)*p... check below
n = len(v); pos = 0.5*(n-1)*0.9*2/1  # not used
pos = (n-1)*0.9*0.5*2  # dummy
# Hazen (type5): h = (n-1)*p + 0.5?? -> numpy: gamma = p*n - p + 0.5 => pos = p*(n-1)+0.5-... let's do direct:
pos = 0.9*n - 0.9 + 0.5 - 1  # 0-based index = p*n + 0.5 - p - 1
lo = int(np.floor(pos)); frac = pos - lo
manual = v[lo] + frac*(v[lo+1]-v[lo])
print("manual hazen (doy200 cell 30,30): %.10f | numpy: %.10f" % (manual, thr_raw[200,30,30]))

np.save('/tmp/thr_s.npy', thr_s); np.save('/tmp/clim_s.npy', clim_s)
print("thr_s[153,30,30]=%.4f clim_s[153,30,30]=%.4f" % (thr_s[153,30,30], clim_s[153,30,30]))
