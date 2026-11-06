import h5py, numpy as np
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
raw = np.asarray(f['time'])
# index of date = (date - 1981-01-01).days
import datetime
def i_of(y,m,dd):
    return (datetime.date(y,m,dd) - datetime.date(1981,1,1)).days
i0101 = i_of(1992,1,1); i0701 = i_of(1992,7,1)
print("indices:", i0101, i0701)
s1 = np.ascontiguousarray(v[i0101])
s2 = np.ascontiguousarray(v[i0701])
d = s2 - s1
nz = (d != 0) & ~np.isnan(d)
print("1992-01-01 vs 1992-07-01: n diff =", nz.sum(), "finite-mask diff:", (np.isfinite(s1)!=np.isfinite(s2)).sum())
# stats file
st = np.load('/work/slice_stats.npy')
print("stats rows for 3650..3660:")
for i in range(3650, 3661): print(i, st[i])
print("stats row 3834:", st[3834])
f.close()
