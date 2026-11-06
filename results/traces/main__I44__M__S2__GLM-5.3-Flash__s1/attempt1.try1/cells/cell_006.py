import h5py, numpy as np, time
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r")
d = f["analysed_sst"]
t0 = time.time()
buf = np.empty((100,60,60), dtype=np.float32)
for i in range(100):
    buf[i] = d[3652+i, 491:551, 616:676]
t1 = time.time()
print("100 days:", t1-t0, "s -> est total for 4120 days:", (t1-t0)*41.2, "s")
f.close()
