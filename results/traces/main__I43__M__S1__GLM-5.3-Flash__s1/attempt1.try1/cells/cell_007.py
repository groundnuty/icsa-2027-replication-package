import h5py, numpy as np, time
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc'
with h5py.File(p, 'r') as f:
    def show(name, obj):
        if isinstance(obj, h5py.Dataset):
            print(name, obj.shape, obj.dtype, 'chunks', obj.chunks, 'compression', obj.compression)
    f.visititems(show)
t0=time.time()
with h5py.File(p, 'r') as f:
    v = f['analysed_sst'][0, 438:498, 487:547]
print('h5py direct read', time.time()-t0, v.shape, v.dtype)
# timing single file full open+read via h5py
t0=time.time()
for i in range(10):
    with h5py.File(f'/data/icsa2027_data_20261101T090944Z/s1z/sst_1992{str(1+i).zfill(2)}01.nc','r') as f:
        v = f['analysed_sst'][0, 438:498, 487:547]
print('10 files h5py', time.time()-t0)
