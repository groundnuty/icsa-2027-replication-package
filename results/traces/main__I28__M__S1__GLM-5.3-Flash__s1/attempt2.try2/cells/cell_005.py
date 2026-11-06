import h5py, numpy as np, os, time
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc"
with h5py.File(p, "r") as f:
    d = f["analysed_sst"]
    print("chunks:", d.chunks, "compression:", d.compression, "shuffle:", d.shuffle, "filters:", d._filters)
print("cpu_count:", os.cpu_count())
# quick timing of a slice read again (cache warm)
t0=time.time()
with h5py.File(p, "r") as f:
    sub = f["analysed_sst"][0, 218:278, 601:661]
print("warm read:", round(time.time()-t0,4), "s")
t0=time.time()
with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_20010504.nc", "r") as f:
    sub = f["analysed_sst"][0, 218:278, 601:661]
print("cold read:", round(time.time()-t0,4), "s", np.isfinite(sub).sum())
