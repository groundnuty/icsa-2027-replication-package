import numpy as np, fsspec, h5py, time, os

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
h5 = h5py.File(f, "r")
sst = h5["analysed_sst"]
lat = h5["latitude"][:]; lon = h5["longitude"][:]
la = lat.astype('float64'); lo = lon.astype('float64')
lat_idx = np.where((la >= 57.57) & (la <= 58.77))[0]
lon_idx = np.where((lo >= 10.25) & (lo <= 11.45))[0]
i0, i1 = int(lat_idx[0]), int(lat_idx[-1])+1
j0, j1 = int(lon_idx[0]), int(lon_idx[-1])+1
print("lat slice", i0, i1, "lon slice", j0, j1)
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
            fails.append((a+k, str(e)[:60]))
            out[k] = np.nan
        if (k+1) % 1000 == 0:
            print(f"  {k+1}/{n} elapsed {time.time()-t0:.1f}s", flush=True)
    np.save(fname, out)
    print(fname, "saved", out.shape, "fails:", len(fails), f"elapsed {time.time()-t0:.1f}s")
    print("  finite frac:", round(float(np.isfinite(out).mean()), 4), "min/max:", float(np.nanmin(out)), float(np.nanmax(out)))
    return fails

fa = read_range(3647, 4646, "/work/parts/ext_a.npy")
print("batch A done")
