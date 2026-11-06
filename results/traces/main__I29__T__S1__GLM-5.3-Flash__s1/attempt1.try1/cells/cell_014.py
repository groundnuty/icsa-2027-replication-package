import fsspec, h5py, numpy as np, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
t0=time.time()
for i in range(30):
    d = 1+i
    f = fs.open(base+'sst_199206%02d.nc'%d,'rb')
    with h5py.File(f,'r') as h:
        reg = h['analysed_sst'][0, 218:278, 601:661].astype(np.float64)
    f.close()
t1=time.time()
print('30 files h5py', t1-t0, 'per file', (t1-t0)/30)
f = fs.open(base+'sst_19820101.nc','rb')
with h5py.File(f,'r') as h:
    print('root attrs:', dict(h.attrs))
    tt = h['time']
    print('time attrs', dict(tt.attrs), 'vals', tt[:])
    print('lat keys', list(h['latitude'].attrs.keys()), 'lat', h['latitude'][218:221])
f.close()
