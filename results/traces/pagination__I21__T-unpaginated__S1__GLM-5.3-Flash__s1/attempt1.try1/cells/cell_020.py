import numpy as np, datetime as dt, pickle, warnings

base = np.load('/tmp/base_cube.npy')
with open('/tmp/pools.pkl','rb') as f: pools = pickle.load(f)

clim_raw = np.full((367,60,60), np.nan)   # index 0 unused; doy d at index d
thr_raw  = np.full((367,60,60), np.nan)
pool_tot = np.zeros(367, dtype=np.int64)
t0 = dt.datetime.now()
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    for doy, idxs in pools.items():
        vals = base[idxs]
        pool_tot[doy] = np.isfinite(vals).sum()
        flat = vals.reshape(len(idxs), -1)
        thr_raw[doy] = np.nanquantile(flat, 0.9, axis=0, method='hazen').reshape(60,60)
        clim_raw[doy] = np.nanmean(flat, axis=0).reshape(60,60)
print("quantiles+means took", dt.datetime.now()-t0)
print("pool value counts: min", pool_tot[1:].min(), "max", pool_tot[1:].max(), "doy60:", pool_tot[60])

thr_raw[60]  = 0.5*(thr_raw[59]  + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])
land = 3600-3314
print("NaN in thr_raw/clim_raw (land-only expected %d):" % (land*367),
      int(np.isnan(thr_raw).sum()), int(np.isnan(clim_raw).sum()))

def smooth31(a367):  # input (367,60,60) with doy at index d; returns same layout
    a = a367[1:]                       # (366,60,60), element i = doy i+1
    out = np.empty_like(a)
    for d in range(366):
        idx = [(d+k) % 366 for k in range(-15, 16)]
        out[d] = a[idx].mean(axis=0)
    res = np.full_like(a367, np.nan)
    res[1:] = out
    return res
thr_s  = smooth31(thr_raw)
clim_s = smooth31(clim_raw)
print("smoothed finite count == 3314*366:",
      int(np.isfinite(thr_s).sum()) == 3314*366, int(np.isfinite(clim_s).sum()) == 3314*366)
np.save('/tmp/thr_s.npy', thr_s); np.save('/tmp/clim_s.npy', clim_s)

doy = 200
v = np.sort(base[pools[doy]][:, 30, 30])
n = len(v); pos = 0.9*n + 0.5 - 0.9 - 1
lo = int(np.floor(pos)); frac = pos - lo
manual = v[lo] + frac*(v[lo+1]-v[lo])
print("manual hazen doy200 cell(30,30): %.10f | numpy: %.10f" % (manual, thr_raw[doy,30,30]))
print("thr_s[153,30,30]=%.4f clim_s[153,30,30]=%.4f" % (thr_s[153,30,30], clim_s[153,30,30]))
print("thr_s sea-cell range: %.3f .. %.3f | clim_s: %.3f .. %.3f" %
      (np.nanmin(thr_s), np.nanmax(thr_s), np.nanmin(clim_s), np.nanmax(clim_s)))
