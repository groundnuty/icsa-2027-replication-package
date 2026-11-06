import h5py, numpy as np, time as tm
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r")
dset = f["analysed_sst"]
time_dset = f["time"]
print("time attrs:", dict(time_dset.attrs))
t0 = tm.time()
block = dset[100, 180:240, 690:750]   # some day, region slice guess
print("read time:", tm.time()-t0, block.shape, block.dtype)
print(block[:3,:3])
t0 = tm.time()
block = dset[100, 180:240, 690:750]
print("second read (cached?):", tm.time()-t0)
