import numpy as np, h5py, os, datetime as dt
cache = "/work/cache"
blocks = sorted(os.listdir(cache))
print("n blocks:", len(blocks), blocks[:3], blocks[-3:])
start = dt.date(1991,12,27)
# concat check shapes
shapes = set()
for b in blocks:
    shapes.add(np.load(os.path.join(cache, b), mmap_mode="r").shape)
print("shapes:", shapes)

# spot check 5 random dates
rng = np.random.default_rng(0)
for i in rng.choice(7919, 5, replace=False):
    d = start + dt.timedelta(days=int(i))
    b = i // 128
    arr = np.load(os.path.join(cache, "block_%02d.npy" % b), mmap_mode="r")
    k = i - b*128
    cached = np.array(arr[k])
    with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_"+d.strftime("%Y%m%d")+".nc", "r") as f:
        fresh = f["analysed_sst"][0, 218:278, 601:661]
    same = np.array_equal(cached, fresh, equal_nan=True)
    print(d, "match:", same, "finite:", np.isfinite(cached).sum())
