import h5py, numpy as np, time, os, datetime as dt, pickle

DIR = "/data/icsa2027_data_20261101T090944Z/s1z"
lat_idx = np.load("output/lat_idx.npy"); lon_idx = np.load("output/lon_idx.npy")

def day_range(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)

def read_day(d):
    p = f"{DIR}/sst_{d:%Y%m%d}.nc"
    with h5py.File(p, "r") as f:
        v = f["analysed_sst"][0][lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    return v.astype(np.float32)

t_start = dt.date(2004,6,1); t_end = dt.date(2004,8,31)
days = list(day_range(t_start, t_end))
print("target days:", len(days), days[0], days[-1])
arr = np.empty((len(days), 60, 60), dtype=np.float32)
t0 = time.time()
for i, d in enumerate(days):
    arr[i] = read_day(d)
    if (i+1) % 20 == 0:
        print(i+1, d, "%.1f s" % (time.time()-t0), flush=True)
print("total %.1f s, finite frac %.4f, min %.2f max %.2f" % (
    time.time()-t0, np.isfinite(arr).mean(), np.nanmin(arr), np.nanmax(arr)))
np.save("output/tgt_sst.npy", arr)
with open("output/tgt_days.pkl", "wb") as fh:
    pickle.dump([d.isoformat() for d in days], fh)
print("saved")
