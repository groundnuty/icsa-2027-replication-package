import numpy as np, h5py
PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
EPOCH = np.datetime64("1970-01-01")
with h5py.File(PATH, "r") as f:
    times = EPOCH + f["time"][:].astype("timedelta64[s]")
    i0b = np.searchsorted(times, np.datetime64("1991-12-27"))
    i1b = np.searchsorted(times, np.datetime64("2003-01-05"), side="right")
    base_now = f["analysed_sst"][i0b:i1b, 182:242, 690:750].astype(np.float64)
print("indices:", i0b, i1b)
old = np.load("/tmp/base.npy")
print("shapes:", base_now.shape, old.shape, "dtypes:", base_now.dtype, old.dtype)
diff = base_now != old
bothnan = np.isnan(base_now) & np.isnan(old)
real_diff = diff & ~bothnan
print("n real diffs:", real_diff.sum(), "of", base_now.size)
print("nan pattern identical:", np.array_equal(np.isnan(base_now), np.isnan(old)))
idx = np.argwhere(real_diff)[:5]
for a, b, c in idx:
    print(a, b, c, base_now[a,b,c], old[a,b,c])
