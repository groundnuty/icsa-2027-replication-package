import h5py, numpy as np
f = h5py.File('/work/data/sst_20040715.nc', 'r')
def show(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(name, obj.shape, obj.dtype, list(obj.keys()) if hasattr(obj,'keys') else '')
    else:
        print(name, "GROUP")
f.visititems(show)
print("root attrs:", dict(f.attrs))
v = f['analysed_sst']
print("var attrs:", dict(v.attrs))
print("time var:", f['time'][:], dict(f['time'].attrs))
print("latitude var:", f['latitude'][:3], dict(f['latitude'].attrs))
print("longitude var:", f['longitude'][:3], dict(f['longitude'].attrs))
f.close()
