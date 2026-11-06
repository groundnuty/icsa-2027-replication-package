import h5py, numpy as np, time, os
p = "/tmp/persist_test.txt"
print("persist test:", open(p).read() if os.path.exists(p) else "NEW FILE (first run)")
open(p,"w").write("hello")

f = h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc","r")
v = f["analysed_sst"]
print("chunks:", v.chunks, "shape:", v.shape, "dtype:", v.dtype)
t0=time.time()
x = v[0, 156:217, 561:622]  # guess region slice
print("read time", time.time()-t0, x.shape)
t0=time.time()
x2 = v[:, :, :]
print("full read time", time.time()-t0, x2.shape)
f.close()
