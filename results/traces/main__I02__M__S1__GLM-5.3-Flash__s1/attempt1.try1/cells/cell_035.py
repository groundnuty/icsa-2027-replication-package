import numpy as np, h5py, datetime as dt, random
D='/data/icsa2027_data_20261101T090944Z/s1z'
bdata=np.load('/tmp/baseline.npy', mmap_mode='r')
bdates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]
random.seed(42)
mis=0
sample=random.sample(range(len(bdates)), 60)
for i in sample:
    d=bdates[i]
    with h5py.File(f'{D}/sst_{d:%Y%m%d}.nc','r') as f:
        a=f['analysed_sst'][0,34:94,213:273]
    c=bdata[i]
    if not np.array_equal(a, c, equal_nan=True):
        mis+=1; print("MISMATCH", d)
print("baseline value mismatches:", mis, "/", len(sample))
# target: verify all 92
tdata=np.load('/tmp/target.npy', mmap_mode='r')
tdates=[dt.date(2004,6,1)+dt.timedelta(days=i) for i in range(tdata.shape[0])]
mis=0
for i,d in enumerate(tdates):
    with h5py.File(f'{D}/sst_{d:%Y%m%d}.nc','r') as f:
        a=f['analysed_sst'][0,34:94,213:273]
    if not np.array_equal(a, tdata[i], equal_nan=True):
        mis+=1; print("T MISMATCH", d)
print("target value mismatches:", mis, "/ 92")
