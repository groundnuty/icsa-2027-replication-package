import numpy as np, datetime as dt, pickle, warnings

base = np.load('/tmp/base_cube.npy')
with open('/tmp/pools.pkl','rb') as f: pools = pickle.load(f)

clim_raw = np.full((366,60,60), np.nan)
thr_raw  = np.full((366,60,60), np.nan)
pool_tot = np.zeros(366, dtype=np.int64)
t0 = dt.datetime.now()
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN slices = land cells, expected
    for doy, idxs in pools.items():
        vals = base[idxs]
        pool_tot[doy] = np.isfinite(vals).sum()
        flat = vals.reshape(len(idxs), -1)
        thr_raw[doy] = np.nanquantile(flat, 0.9, axis=0, method='hazen').reshape(60,60)
        clim_raw[doy] = np.nanmean(flat, axis=0).reshape(60,60)
print("quantiles+means took", dt.datetime.now()-t0)
print("pool value counts: min", pool_tot[pool_tot>0].min(), "max", pool_tot.max(), "doy60:", pool_tot[60])

thr_raw[60]  = 0.5*(thr_raw[59]  + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])
print("NaN remaining in thr_raw/clim_raw (land only expected):",
      int(np.isnan(thr_raw).sum()), int(np.isnan(clim_raw).sum()),
      "| land cells:", 3600-3314, "x366 =", (3600-3314)*366)

def smooth31(a):
    out = np.empty_like(a)
    for d in range(366):
        idx = [(d+k) % 366 for k in range(-15, 16)]
        out[d] = a[idx].mean(axis=0)
    return out
thr_s  = smooth31(thr_raw)
clim_s = smooth31(clim_raw)
print("smoothed finite everywhere on sea cells:",
      np.isfinite(thr_s[:, :]).all() if False else bool(np.isfinite(thr_s).sum() == 3314*366),
      bool(np.isfinite(clim_s).sum() == 3314*366))
np.save('/tmp/thr_s.npy', thr_s); np.save('/tmp/clim_s.npy', clim_s)

# manual hazen check for one pool/cell
doy = 200
v = np.sort(base[pools[doy]][:, 30, 30])
n = len(v); pos = 0.9*n + 0.5 - 0.9 - 1
lo = int(np.floor(pos)); frac = pos - lo
manual = v[lo] + frac*(v[lo+1]-v[lo])
print("manual hazen doy200 cell(30,30): %.10f | numpy: %.10f" % (manual, thr_raw[doy,30,30]))
# spot values
print("thr_s[153,30,30]=%.4f clim_s[153,30,30]=%.4f" % (thr_s[153,30,30], clim_s[153,30,30]))
print("thr_s range on sea cells: %.3f .. %.3f" % (np.nanmin(thr_s), np.nanmax(thr_s)))
print("clim_s range on sea cells: %.3f .. %.3f" % (np.nanmin(clim_s), np.nanmax(clim_s)))
