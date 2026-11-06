import numpy as np
from scipy.stats.mstats import mquantiles
base = np.load('/tmp/base_cube.npy')
import pickle
with open('/tmp/pools.pkl','rb') as f: pools = pickle.load(f)

cells = [(30,30),(5,5),(55,55),(10,50),(0,2)]
ok = True
for doy in [1, 59, 200, 366, 150]:
    for (i,j) in cells:
        vv = base[pools[doy]][:, i, j]
        vv = vv[~np.isnan(vv)]
        if vv.size == 0: continue
        q_np = np.quantile(vv, 0.9, method='hazen')
        q_sc = np.asarray(mquantiles(vv, prob=0.9, alphap=0.5, betap=0.5)).ravel()[0]
        if not np.isclose(float(q_np), float(q_sc), rtol=0, atol=1e-10):
            ok = False; print("MISMATCH", doy, i, j, q_np, q_sc)
print("scipy(alphap=betap=0.5) == numpy hazen on all samples:", ok)

# brute-force recompute of one full pool directly from source files, one cell
import fsspec, h5py, datetime as dt
fs = fsspec.filesystem('onedata'); b = 'icsa2027_data_20261101T090944Z/s1z'
idxs = pools[150]
dvals = []
for k in idxs:
    d = dt.date(1991,12,27)+dt.timedelta(days=int(k))
    with fs.open(f"{b}/sst_{d.strftime('%Y%m%d')}.nc",'rb') as f:
        with h5py.File(f,'r') as hf:
            dvals.append(hf['analysed_sst'][0, 192+30, 2+30])
dvals = np.array(dvals, dtype=np.float64)
raw = base[idxs][:,30,30]
print("direct-from-files pool n=%d" % len(dvals),
      "| values == cube values:", bool(np.array_equal(np.nan_to_num(dvals,nan=-999), np.nan_to_num(raw,nan=-999))),
      "| q direct: %.6f | q cube: %.6f | mean direct: %.6f | mean cube: %.6f" %
      (np.quantile(dvals[~np.isnan(dvals)],0.9,method='hazen'),
       np.quantile(raw[~np.isnan(raw)],0.9,method='hazen'),
       np.nanmean(dvals), np.nanmean(raw)))
# spans of a mid-year pool
d0 = dt.date(1991,12,27)
print("doy150 pool dates: %s .. %s (n=%d)" % (d0+dt.timedelta(days=int(idxs[0])), d0+dt.timedelta(days=int(idxs[-1])), len(idxs)))
