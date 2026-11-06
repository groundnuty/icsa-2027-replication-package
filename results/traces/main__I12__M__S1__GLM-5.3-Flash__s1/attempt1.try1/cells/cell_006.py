import h5py, numpy as np, time
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc'
with h5py.File(p, 'r') as f:
    def show(name, obj):
        if isinstance(obj, h5py.Dataset):
            print(name, obj.shape, obj.dtype, 'chunks', obj.chunks, 'compression', obj.compression)
            print('  attrs:', {k: obj.attrs[k] for k in obj.attrs})
    f.visititems(show)
    t0 = time.time()
    sub = f['analysed_sst'][0, 130:190, 78:138]
    print('subset read time', time.time()-t0, sub.dtype, sub.shape)
    print(sub[:2,:3,:3])
