import h5py, numpy as np, time, json
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
dates = json.load(open("/tmp/mhw/dates.json"))["base_win"]
nb = np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r+", shape=(len(dates), 3600))

def load_chunk(dsl, rows, arr):
    t0 = time.time()
    for k, d in enumerate(dsl):
        with h5py.File(f"{BASE}/sst_{d.replace('-','')}.nc", "r") as f:
            sl = f["analysed_sst"][0, 322:382, 485:545][:]
        arr[rows[k]] = sl.astype(np.float64).ravel()
    arr.flush()
    return time.time() - t0

s = 2400
secs = load_chunk(dates[s:s+1628], range(s, s+1628), nb)
print(f"baseline rows {s}..{len(dates)}: {secs:.1f}s; done={s+1628}/{len(dates)}")
