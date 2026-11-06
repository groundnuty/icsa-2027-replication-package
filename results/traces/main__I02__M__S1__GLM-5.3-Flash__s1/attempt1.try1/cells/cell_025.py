import numpy as np, h5py, datetime as dt, random
D='/data/icsa2027_data_20261101T090944Z/s1z'
bdata=np.load('/tmp/baseline.npy', mmap_mode='r')
bdates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]
random.seed(0)
sample=random.sample(range(len(bdates)), 25)
mismatch=0
for i in sample:
    d=bdates[i]
    fn=f'{D}/sst_{d:%Y%m%d}.nc'
    with h5py.File(fn,'r') as f:
        a=f['analysed_sst'][0]
    same=np.array_equal(np.isfinite(a), np.isfinite(bdata[i]))
    if not same:
        mismatch+=1
        diff=np.isfinite(a)^np.isfinite(bdata[i])
        print(f"{d} pattern differs at {diff.sum()} cells; cached finite frac {np.isfinite(bdata[i]).mean():.4f} fresh {np.isfinite(a).mean():.4f}")
print("mismatched files in sample:", mismatch, "/", len(sample))
