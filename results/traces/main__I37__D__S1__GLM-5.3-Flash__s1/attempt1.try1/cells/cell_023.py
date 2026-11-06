import h5py, numpy as np
p = '/work/data/sst_19920601.nc'
with h5py.File(p,'r') as f:
    t = f['time']
    print("time attrs:", dict(t.attrs), "raw:", t[:][0])
    v = f['analysed_sst']
    print("sst attrs:", {k: v.attrs[k] for k in v.attrs})
    print("sst dtype:", v.dtype, "shape:", v.shape, "chunks:", v.chunks)
    raw = v[0, 329:390, 550:611]
    print("raw sample:", raw[:3,:5])
