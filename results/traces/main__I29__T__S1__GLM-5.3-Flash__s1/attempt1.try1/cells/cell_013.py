import fsspec, h5py, numpy as np, time, json
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
t0=time.time()
tot=0.0
for i in range(50):
    d = 1+i
    f = fs.open(base+'sst_199206%02d.nc'%d,'rb')
    with h5py.File(f,'r') as h:
        reg = h['analysed_sst'][0, 218:278, 601:661].astype(np.float64)
    f.close()
    tot += 1
t1=time.time()
print('50 files h5py', t1-t0, 'per file', (t1-t0)/50)
# check first file (has no JSON metadata) for attrs
f = fs.open(base+'sst_19820101.nc','rb')
with h5py.File(f,'r') as h:
    print('root attrs:', list(h.attrs.keys()))
    tt = h['time']
    print('time attrs', dict(tt.attrs), 'vals', tt[:])
    print('lat attrs', dict(h['latitude'].attrs)[:0] if False else list(h['latitude'].attrs.keys()))
    print('lat', h['latitude'][218:221], 'lon', h['longitude'][601:604])
f.close()
