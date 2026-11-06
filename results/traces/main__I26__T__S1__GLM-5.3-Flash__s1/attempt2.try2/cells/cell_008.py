import fsspec, xarray as xr, numpy as np, io, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
d='20070601'
data = fs.cat([f'{base}/sst_{d}.nc'])
b = data[f'{base}/sst_{d}.nc']
# raw read via h5py to inspect storage
import h5py
f = h5py.File(io.BytesIO(b),'r')
def show(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(name, obj.dtype, obj.shape, dict(obj.attrs), 'chunks', obj.chunks, 'compress', obj.compression, 'scaleoffset', obj.scaleoffset)
f.visititems(show)
print(list(f.attrs.items())[:5])
t0=time.time()
arr = f['analysed_sst'][0]
t1=time.time()
print('h5py raw read', t1-t0, arr.dtype, arr[:2,:2])
sf = f['analysed_sst'].attrs.get('scale_factor'); ao=f['analysed_sst'].attrs.get('add_offset')
if sf is not None:
    x = arr.astype('float64')*np.float64(sf)+ (float(ao) if ao is not None else 0.0)
    print(x[:2,:2])
f.close()
