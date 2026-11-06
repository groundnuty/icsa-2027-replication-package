import numpy as np
from scipy.stats.mstats import mquantiles
base = np.load('/tmp/base_cube.npy')
import pickle
with open('/tmp/pools.pkl','rb') as f: pools = pickle.load(f)

v = np.sort(base[pools[200]][:, 30, 30])
n = len(v)
pos = n*0.9 - 0.5
lo = int(np.floor(pos)); frac = pos - lo
manual = v[lo] + frac*(v[lo+1]-v[lo])
print("corrected manual (pos=np-0.5): %.10f | numpy: %.10f | match: %s" %
      (manual, np.quantile(v, 0.9, method='hazen'), np.isclose(manual, np.quantile(v,0.9,method='hazen'), rtol=0, atol=1e-9)))

# scipy mquantiles with alphap=betap=0.5 (plotting position (j-0.5)/n) on several pools/cells
import random
random.seed(1)
cells = [(30,30),(5,5),(55,55),(10,50)]
ok = True
for doy in [1, 59, 200, 366]:
    for (i,j) in cells:
        vv = base[pools[doy]][:, i, j]
        if np.isnan(vv).all(): continue
        q_np = np.quantile(vv[~np.isnan(vv)], 0.9, method='hazen')
        q_sc = float(mquantiles(vv[~np.isnan(vv)], prob=0.9, alphap=0.5, betap=0.5))
        if not np.isclose(q_np, q_sc, rtol=0, atol=1e-10):
            ok = False; print("MISMATCH", doy, i, j, q_np, q_sc)
print("scipy (alphap=betap=0.5) == numpy hazen on samples:", ok)

# brute-force recompute of one full pool quantile + mean directly from source files for one cell
import fsspec, h5py, datetime as dt, time
fs = fsspec.filesystem('onedata'); b = 'icsa2027_data_20261101T090944Z/s1z'
idxs = pools[150]
dvals = []
for k in idxs:
    d = dt.date(1991,12,27)+dt.timedelta(days=int(k))
    with fs.open(f"{b}/sst_{d.strftime('%Y%m%d')}.nc",'rb') as f:
        with h5py.File(f,'r') as hf:
            dvals.append(hf['analysed_sst'][0, 192+30, 2+30])
dvals = np.array(dvals, dtype=np.float64)
q_direct = np.quantile(dvals[~np.isnan(dvals)], 0.9, method='hazen')
m_direct = np.nanmean(dvals)
cube_q = np.load('/tmp/thr_s.npy')[150,30,30]  # smoothed! compare via raw
# recompute raw from cube
raw = base[idxs][:,30,30]
print("direct-from-files pool n=%d | q=%.6f | cube q(raw)=%.6f | mean=%.6f vs cube raw mean=%.6f" %
      (len(dvals), q_direct, np.quantile(raw[~np.isnan(raw)],0.9,method='hazen'), m_direct, np.nanmean(raw)))
print("direct values equal cube values:", np.allclose(np.nan_to_num(dvals,nan=-999), np.nan_to_num(raw,nan=-999)))
