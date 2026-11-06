import h5py, numpy as np, time, os
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20040710.nc"
t0 = time.time()
with h5py.File(p, "r") as f:
    print("open:", time.time()-t0)
    print(list(f.keys()))
    ds = f["analysed_sst"]
    print("shape:", ds.shape, "dtype:", ds.dtype, "chunks:", ds.chunks, "maxshape:", ds.maxshape)
    t0 = time.time()
    full = ds[0, 204:264, 63:123]  # h5py selection read
    t1 = time.time()
    print("slice read:", t1-t0, full.shape, full.dtype)
    print("fill:", ds.fillvalue)
    # check attrs
    for k, v in ds.attrs.items():
        print("attr", k, v)
