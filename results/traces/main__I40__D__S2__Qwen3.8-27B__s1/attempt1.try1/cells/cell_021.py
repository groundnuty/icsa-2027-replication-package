import h5py, numpy as np
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
la = np.asarray(f['latitude']); lo = np.asarray(f['longitude'])
s_a = np.ascontiguousarray(v[3652])   # 1992-01-01
s_b = np.ascontiguousarray(v[3653])   # 1992-01-02
s_c = np.ascontiguousarray(v[3817])   # 1992-07-01
s_0 = np.ascontiguousarray(v[0])      # 1982-01-01

def describe(name, d):
    nz = np.where((d != 0) & (np.isfinite(d) | np.isfinite(np.broadcast_to(0, d.shape)*0) | np.isnan(d)), (d!=0))
    nz = d != 0
    nz &= ~np.isnan(d)
    ys, xs = np.where(nz)
    if ys.size:
        print(f"{name}: n={ys.size} dmin={d[ys,xs].min():.6g} dmax={d[ys,xs].max():.6g} "
              f"lat {la[ys.min()]:.2f}..{la[ys.max()]:.2f} lon {lo[xs.min()]:.2f}..{lo[xs.max()]:.2f}")
    else:
        print(name, "zero")
    # also nan-status changes
    return nz

nz_ab = (np.isfinite(s_a) != np.isfinite(s_b))
print("finite-mask changes a vs b:", nz_ab.sum())
describe("1992-01-02 minus 1992-01-01", s_b - s_a)
describe("1992-07-01 minus 1992-01-01", s_c - s_a)
nz_0 = (s_0 != s_a) & (np.isfinite(s_0) | np.isfinite(s_a))
ys, xs = np.where(nz_0)
print("1982-01-01 vs 1992-01-01: n =", ys.size,
      "dmin %.4g dmax %.4g" % ((s_0-s_a)[ys,xs].min(), (s_0-s_a)[ys,xs].max()))
# spatial structure of 1982 vs 1992 diff: row/col histogram
import collections
print("diff by latitude band (5-deg):")
for lb in range(53, 67, 5):
    m = (la >= lb) & (la < lb+5)
    print(f"  {lb}-{lb+5}N: {int(nz_0[m].sum())}")
f.close()
