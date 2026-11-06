import h5py, numpy as np, os, time, datetime as dt

BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
OUT = "/work/mhw"
I0, I1, J0, J1 = 204, 264, 63, 123
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=k) for k in range(4028)]

def load_batch(a, b, tag="base"):
    path = f"{OUT}/{tag}_{a:04d}_{b:04d}.npy"
    if os.path.exists(path):
        print("skip existing", path); return
    buf = np.empty((b-a, 60, 60), dtype=np.float64)
    t0 = time.time(); fails = []
    for k in range(a, b):
        d = dates[k]
        try:
            with h5py.File(os.path.join(BASE, f"sst_{d:%Y%m%d}.nc"), "r") as f:
                v = f["analysed_sst"][0, I0:I1, J0:J1]
            v = np.asarray(v, dtype=np.float64)
            assert v.shape == (60,60)
            buf[k-a] = v
        except Exception as e:
            fails.append((d, str(e)))
    if fails:
        print("FAILS:", fails[:5]); raise SystemExit(1)
    np.save(path, buf)
    print(f"batch {tag} {a}:{b} in {time.time()-t0:.1f}s")

for a, b in [(500,1000),(1000,1500)]:
    load_batch(a,b)
