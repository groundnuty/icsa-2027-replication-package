import h5py, numpy as np, datetime
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
raw = np.asarray(f['time'])
print("idx3834 date:", datetime.datetime(1981,1,1) + datetime.timedelta(seconds=int(raw[3834])))
s1 = np.ascontiguousarray(v[3652])
s2 = np.ascontiguousarray(v[3834])
d = s2 - s1
nz = (d != 0) & ~np.isnan(d)
print("1992-01-01 vs 1992-07-01: n diff =", nz.sum(), "finite-mask diff:", (np.isfinite(s1)!=np.isfinite(s2)).sum())
# Also compare consecutive days 3652/3653 (1992-01-01/02) and 3652 vs 3656 (Jan 5)
for j in [3653, 3656, 3700, 3782, 3833, 3835, 4000, 4016, 4018, 4019]:
    sj = np.ascontiguousarray(v[j])
    dj = s1 - sj
    nj = (dj != 0) & ~np.isnan(dj)
    md = int(raw[j])//86400
    print(j, datetime.date(1981,1,1)+datetime.timedelta(days=md), "ndiff vs 1992-01-01:", nj.sum())
f.close()
