import numpy as np, h5py, datetime as dt, random
D='/data/icsa2027_data_20261101T090944Z/s1z'
bdata=np.load('/tmp/baseline.npy', mmap_mode='r')
bdates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]
i=bdates.index(dt.date(1992,6,1))
with h5py.File(f'{D}/sst_19920601.nc','r') as f:
    a=f['analysed_sst'][0,34:94,213:273]
c=bdata[i]
print("1992-06-01: pattern equal:", np.array_equal(np.isfinite(a),np.isfinite(c)),
      " values equal:", np.array_equal(a,c,equal_nan=True))
diff=np.isfinite(a)^np.isfinite(c)
ys,xs=np.where(diff); print("  pattern diffs:", diff.sum(), list(zip(ys[:10],xs[:10])))
vd=np.abs(np.where(np.isfinite(a)&np.isfinite(c), a-c, 0)); print("  max |value diff| (both finite):", vd.max())
# value comparison on random sample (not just patterns)
random.seed(1)
sample=random.sample(range(len(bdates)), 30)
nmis=0; nval=0
for i in sample:
    d=bdates[i]
    with h5py.File(f'{D}/sst_{d:%Y%m%d}.nc','r') as f:
        a=f['analysed_sst'][0,34:94,213:273]
    c=bdata[i]
    if not np.array_equal(np.isfinite(a),np.isfinite(c)): nmis+=1
    else:
        m=np.isfinite(a)
        if m and not np.allclose(a[m],c[m],rtol=0,atol=0): nval+=1
print("sample: pattern mismatches:", nmis, "value mismatches:", nval)
