import h5py, time, numpy as np, xarray as xr
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r"); d = f["analysed_sst"]
t0 = time.time()
acc = 0
for k in range(200, 300):
    a = d[k, 322:382, 485:545]
    acc += np.isfinite(a).sum()
t1 = time.time()
print("100 planes sub-box:", round(t1-t0, 3), "s ->", round((t1-t0)/100*8056/60, 2), "min for ~8056 planes (sub-box)")
t0 = time.time()
for k in range(200, 300):
    a = d[k, :, :]
t1 = time.time()
print("100 planes full:", round(t1-t0, 3), "s ->", round((t1-t0)/100*8056/60, 2), "min for ~8056 planes (full)")
f.close()
