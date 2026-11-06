import h5py, numpy as np, os, time, datetime as dt

BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
OUT = "/work/mhw"
I0, I1, J0, J1 = 204, 264, 63, 123
os.makedirs(OUT, exist_ok=True)
base_dates = [dt.date(1991,12,27) + dt.timedelta(days=k) for k in range(4028)]

def load_range(dates, a, b, tag):
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

# finish baseline 2500:4028 in two chunks
for a,b in [(2500,3300),(3300,4028)]:
    load_range(base_dates, a, b, "base")

# target 2004-06-01..2004-08-31
tgt_dates = [dt.date(2004,6,1) + dt.timedelta(days=k) for k in range(92)]
load_range(tgt_dates, 0, 92, "tgt")

print("done")
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT,f)))
