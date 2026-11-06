import fsspec, h5py, numpy as np, time
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc'
t0=time.time()
with fs.open(p,'rb') as f:
    with h5py.File(f,'r') as h:
        print(list(h.keys()))
        def show(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(name, obj.shape, obj.dtype, dict(obj.attrs))
        h.visititems(show)
        arr = h['analysed_sst'][0, 350:410, 413:473]
print('read time', time.time()-t0)
print(arr.dtype, arr.shape, np.isnan(arr).mean(), np.nanmin(arr), np.nanmax(arr))
