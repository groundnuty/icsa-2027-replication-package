import fsspec, os, time
fs = fsspec.filesystem('onedata')
os.makedirs('/work/tmp', exist_ok=True)
t0=time.time()
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_20040615.nc', '/work/tmp/one.nc')
t1=time.time()
print('download seconds:', t1-t0)
print('size bytes:', os.path.getsize('/work/tmp/one.nc'))
import h5py
f = h5py.File('/work/tmp/one.nc','r')
def show(name, obj):
    if isinstance(obj, h5py.Dataset):
        print('DS', name, obj.shape, obj.dtype, dict(obj.attrs))
    else:
        print('GR', name)
f.visititems(show)
print('root attrs:', dict(f.attrs))
