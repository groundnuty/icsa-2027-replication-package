import fsspec, h5py, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 404,463,559,618

t0=time.time()
with fs.open(f'{base}/sst_19920101.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        d = hf['analysed_sst']
        print('h5 shape', d.shape, d.dtype, 'chunks', d.chunks, 'fill', d.fillvalue)
        print('attrs', dict(d.attrs))
        arr = d[0, i0:i1+1, j0:j1+1]
t1=time.time()
print('read 1992 subregion: %.3fs' % (t1-t0), arr.shape, arr.dtype)
print('finite frac', np.isfinite(arr).mean())
# second read (cache warm?)
t0=time.time()
with fs.open(f'{base}/sst_19920102.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        arr2 = hf['analysed_sst'][0, i0:i1+1, j0:j1+1]
t1=time.time()
print('read 19920102: %.3fs' % (t1-t0))
