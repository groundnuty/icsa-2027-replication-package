import h5py, time, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20120615.nc"
with h5py.File(p, "r") as f:
    d = f["analysed_sst"]
    print("chunks:", d.chunks, "compression:", d.compression, "shape:", d.shape)
    t0 = time.time()
    sub = d[0, 435:495, 485:545]
    t1 = time.time()
    print("subset read time:", t1-t0, "shape:", sub.shape)
    print(sub[:3,:3])
    print("NaN fraction in region:", np.isnan(sub).mean())
    # time full read for comparison
    t0 = time.time()
    full = d[0, :, :]
    t1 = time.time()
    print("full read time:", t1-t0)
