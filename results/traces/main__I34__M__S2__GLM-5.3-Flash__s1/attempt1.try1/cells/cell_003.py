import h5py, time, numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r")
d = f["analysed_sst"]
print("chunks:", d.chunks, "compression:", d.compression, "shuffle:", d.shuffle, "filters:", d._filters)
t0 = time.time()
a = d[100, 322:382, 485:545]  # single day sub-box
t1 = time.time()
print("single sub-box read:", round(t1-t0, 3), "s, shape", a.shape, "finite frac", np.isfinite(a).mean())
t0 = time.time()
b = d[100, :, :]  # full plane
t1 = time.time()
print("full plane read:", round(t1-t0, 3), "s, shape", b.shape, "MB", b.nbytes/1e6)
t0 = time.time()
c = d[100:104, 322:382, 485:545]
t1 = time.time()
print("4-day sub-box read:", round(t1-t0, 3), "s")
f.close()
