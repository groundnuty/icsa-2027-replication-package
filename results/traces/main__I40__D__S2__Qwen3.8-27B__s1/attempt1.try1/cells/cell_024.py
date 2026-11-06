import h5py, numpy as np
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
raw = np.asarray(f['time'])
# confirm mapping: raw[0], and raw at a few known indices
print("raw[0] =", raw[0], "-> 1982-01-01" if raw[0]==31536000 else "?")
print("raw[3652] =", raw[3652], "should be 1992-01-01:", 3652*86400+31536000)
import datetime
print(datetime.datetime(1981,1,1) + datetime.timedelta(seconds=raw[3652]))
print(datetime.datetime(1981,1,1) + datetime.timedelta(seconds=raw[3834]))
s1 = np.ascontiguousarray(v[3652])
s2 = np.ascontiguousarray(v[3834])
d = s2 - s1
nz = (d != 0) & ~np.isnan(d)
print("idx 3652 vs 3834: n diff =", nz.sum(), "finite-mask diff:", (np.isfinite(s1)!=np.isfinite(s2)).sum())
f.close()
