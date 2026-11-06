import h5py, numpy as np
f = h5py.File('/work/sst_s2.nc', 'r')
print(list(f.keys()))
v = f['analysed_sst']
print("shape:", v.shape, "dtype:", v.dtype, "chunks:", v.chunks, "compression:", v.compression)
print("fillvalue:", v.fillvalue)
for name, d in f.items():
    print(name, getattr(d, 'shape', None), getattr(d, 'dtype', None))
f.close()
