import fsspec, os
fs = fsspec.filesystem('onedata')
os.makedirs('/work/daily', exist_ok=True)
for d in ['19911227','19911231','19920101','19920601','20050601']:
    fs.get(f'icsa2027_data_20261101T090944Z/s1z/sst_{d}.nc', f'/work/daily/sst_{d}.nc')
import h5py
f = h5py.File('/work/daily/sst_19920601.nc','r')
def show(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(name, obj.shape, obj.dtype, dict(obj.attrs))
f.visititems(show)
print("global:", dict(f.attrs))
