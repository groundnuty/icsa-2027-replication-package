import numpy as np, fsspec, h5py, time, os

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
h5 = h5py.File(f, "r")
sst = h5["analysed_sst"]
t = h5["time"][:]  # seconds since 1950-01-01 00:00:00
lat = h5["latitude"][:]; lon = h5["longitude"][:]
la = lat.astype('float64'); lo = lon.astype('float64')
lat_idx = np.where((la >= 57.57) & (la <= 58.77))[0]
lon_idx = np.where((lo >= 10.25) & (lo <= 11.45))[0]
i0, i1 = lat_idx[0], lat_idx[-1]+1
j0, j1 = lon_idx[0], lon_idx[-1]+1
print("lat slice", i0, i1, "lon slice", j0, j1)

# time as dates: seconds since 1950-01-01
base = np.datetime64("1950-01-01")
dates = base + t.astype("timedelta64[s]").astype("timedelta64[D]")
print("dates:", dates[0], dates[-1], dates.size)
assert np.all(np.diff(dates) == np.timedelta64(1,"D"))

def di(dstr):
    return int((np.datetime64(dstr) - dates[0]) / np.timedelta64(1,"D"))

EXT0, EXT1 = di("1991-12-27"), di("2003-01-05")
TGT0, TGT1 = di("2004-06-01"), di("2004-08-31")
print("EXT", EXT0, EXT1, dates[EXT0], dates[EXT1])
print("TGT", TGT0, TGT1, dates[TGT0], dates[TGT1])

os.makedirs("/work/parts", exist_ok=True)

def read_range(a, b, fname):
    n = b - a + 1
    out = np.empty((n, i1-i0, j1-j0), dtype=np.float32)
    t0 = time.time()
    fails = []
    for k in range(n):
        try:
            out[k] = sst[a+k, i0:i1, j0:j1]
        except Exception as e:
            fails.append((a+k, str(e)[:80]))
            out[k] = np.nan
        if (k+1) % 500 == 0:
            print(f"  {k+1}/{n} elapsed {time.time()-t0:.1f}s", flush=True)
    np.save(fname, out)
    print(fname, "saved", out.shape, "fails:", len(fails), f"elapsed {time.time()-t0:.1f}s")
    if fails: print(fails[:5])
    # basic stats
    print("  finite frac:", np.isfinite(out).mean().round(4), "min/max:", np.nanmin(out), np.nanmax(out))
    return fails

read_range(EXT0, 5100, "/work/parts/ext_a.npy")
