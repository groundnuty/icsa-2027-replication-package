import time, fsspec, numpy as np
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
import h5py
t0=time.time()
f = fs.open(base+'sst_19920601.nc','rb')
with h5py.File(f,'r') as h:
    print(list(h.keys()))
    d = h['analysed_sst']
    print(d.shape, d.dtype, dict(d.attrs))
    reg = d[0, 218:278, 601:661]
    print(reg.dtype, np.isnan(reg).sum(), reg[:2,:2])
t1=time.time()
print('h5py time', t1-t0)
t0=time.time()
for i in range(10):
    f = fs.open(base+f'sst_1992{60+i:02d}'.replace('199260','19920601') if False else base+'sst_19920610.nc','rb')
    with h5py.File(f,'r') as h:
        reg = h['analysed_sst'][0, 218:278, 601:661]
t1=time.time()
print('10 files h5py', t1-t0)
