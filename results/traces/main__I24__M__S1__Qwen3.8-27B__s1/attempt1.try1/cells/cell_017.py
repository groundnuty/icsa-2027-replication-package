import h5py, numpy as np, os, time, datetime as dt, sys

BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
OUT = "/work/mhw"
I0, I1, J0, J1 = 204, 264, 63, 123  # region slice (inclusive bounds)
os.makedirs(OUT, exist_ok=True)

start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=k) for k in range(4028)]

def load_batch(a, b, tag="base"):
    path = f"{OUT}/{tag}_{a:04d}_{b:04d}.npy"
    if os.path.exists(path):
        print("skip existing", path)
        return
    buf = np.empty((b-a, 3600), dtype=np.float64)
    t0 = time.time()
    fails = []
    for k in range(a, b):
        d = dates[k]
        fname = f"sst_{d:%Y%m%d}.nc"
        try:
            with h5py.File(os.path.join(BASE, fname), "r") as f:
                v = f["analysed_sst"][0, I0:I1, J0:J1]
            v = np.asarray(v, dtype=np.float64)
            if v.shape != (60,60):
                raise ValueError(f"bad shape {v.shape}")
            buf[k-a] = v
        except Exception as e:
            fails.append((fname, str(e)))
    if fails:
        print("FAILS:", fails[:5])
        raise SystemExit("load failures; not saving batch")
    np.save(path, buf)
    print(f"batch {tag} {a}:{b} saved {path} in {time.time()-t0:.1f}s, mean finite frac={np.isfinite(buf).mean():.4f}")

a, b = int(sys.argv[1]) if len(sys.argv)>1 else 0, int(sys.argv[2]) if len(sys.argv)>2 else 500
load_batch(a, b)
