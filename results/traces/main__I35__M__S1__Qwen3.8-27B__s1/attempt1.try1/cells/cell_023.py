import numpy as np, json, datetime as dt, h5py
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
raw = json.load(open("/tmp/mhw/dates.json"))
dates_b = raw["base_win"]; target = raw["target"]
nb = np.asarray(np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r", shape=(4028, 3600)))
ntf = np.asarray(np.memmap("/tmp/mhw/target.npy", dtype=np.float64, mode="r", shape=(92, 3600)))

rng = np.random.default_rng(0)
ok = True
for _ in range(6):
    i = int(rng.integers(0, 4028)); c = int(rng.integers(0, 3600))
    d = dates_b[i]
    with h5py.File(f"{BASE}/sst_{d.replace('-','')}.nc", "r") as f:
        v = f["analysed_sst"][0, 322:382, 485:545][:][c // 60, c % 60]
    v64 = np.float64(v)
    m = (np.isnan(v64) and np.isnan(nb[i, c])) or (np.isfinite(v64) and np.isclose(v64, nb[i, c]))
    ok &= m
    if not m: print("MISMATCH base", d, c, v64, nb[i, c])
for _ in range(6):
    i = int(rng.integers(0, 92)); c = int(rng.integers(0, 3600))
    d = target[i]
    with h5py.File(f"{BASE}/sst_{d.replace('-','')}.nc", "r") as f:
        v = f["analysed_sst"][0, 322:382, 485:545][:][c // 60, c % 60]
    v64 = np.float64(v)
    m = (np.isnan(v64) and np.isnan(ntf[i, c])) or (np.isfinite(v64) and np.isclose(v64, ntf[i, c]))
    ok &= m
    if not m: print("MISMATCH target", d, c, v64, ntf[i, c])
print("memmap integrity ok:", ok)

# grid boundaries
f = h5py.File(f"{BASE}/sst_20090601.nc", "r")
lat = f["latitude"][:]; lon = f["longitude"][:]
f.close()
for i in (321, 322, 381, 382):
    print("lat idx", i, repr(float(lat[i])), "in region:", 59.93 <= float(lat[i]) <= 61.13)
for j in (484, 485, 544, 545):
    print("lon idx", j, repr(float(lon[j])), "in region:", 18.69 <= float(lon[j]) <= 19.89)
