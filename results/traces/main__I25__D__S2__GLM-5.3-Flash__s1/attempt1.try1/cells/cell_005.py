import numpy as np, h5py
print('numpy', np.__version__)
a = np.array([1.,2,3,4,10, np.nan])
try:
    print('hazen q90:', np.nanquantile(a, 0.9, method='hazen'), 'expect from [1,2,3,4,10]:', None)
except TypeError as e:
    print('no method kw:', e)
# verify manual hazen implementation matches numpy
def hazen_q(x, p):  # x: (n, ...) along axis 0 ignoring nan is separate; this for 1D finite
    x = np.sort(x)
    n = x.size
    h = n*p - 0.5  # 0-based virtual index
    lo = np.floor(h).astype(int); hi = lo + 1
    g = h - lo
    lo = np.clip(lo, 0, n-1); hi = np.clip(hi, 0, n-1)
    return x[lo]*(1-g) + x[hi]*g
fin = a[np.isfinite(a)]
print('manual:', hazen_q(fin, 0.9))
# time continuity
f = h5py.File('/work/sst_s2.nc','r')
t = f['time'][:]
t64 = np.datetime64('1981-01-01') + t.astype('timedelta64[s]')
diffs = np.unique(np.diff(t64).astype('timedelta64[D]').astype(int))
print('unique day diffs:', diffs)
f.close()
import xarray, scipy
print('xarray', xarray.__version__, 'scipy', scipy.__version__)
