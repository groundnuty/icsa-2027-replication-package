import numpy as np, h5py, datetime as dt
D='/data/icsa2027_data_20261101T090944Z/s1z'
bdata=np.load('/tmp/baseline.npy', mmap_mode='r')
bdates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]
d=dt.date(1992,6,1); i=bdates.index(d)
print("index:", i, "date:", bdates[i])
print("cached bdata[157,40,40]:", bdata[i,40,40])
print("cached bdata[157,45,45]:", bdata[i,45,45])
with h5py.File(f'{D}/sst_19920601.nc','r') as f:
    a=f['analysed_sst'][0]
    print("fresh [0,40,40]:", a[40,40], " [0,45,45]:", a[45,45])
    print("fresh finite count:", np.isfinite(a).sum())
# where are the NaNs?
tdata=np.load('/tmp/target.npy')
ys,xs=np.where(~np.isfinite(tdata[0]))
print("nan cell coords sample:", list(zip(ys[:10],xs[:10])))
print("is (40,40) nan in target:", np.isnan(tdata[0,40,40]))
print("row 40 nan count:", np.isnan(tdata[0,40]).sum(), "col 40 nan count:", np.isnan(tdata[0,:,40]).sum())
