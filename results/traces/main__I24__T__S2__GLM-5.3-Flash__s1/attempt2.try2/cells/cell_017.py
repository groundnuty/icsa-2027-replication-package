import numpy as np, fsspec, h5py, time

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
h5 = h5py.File(f, "r")
sst = h5["analysed_sst"]
i0, i1, j0, j1 = 204, 264, 63, 123

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
    np.save(fname, out)
    print(fname, "saved", out.shape, "fails:", len(fails), f"elapsed {time.time()-t0:.1f}s",
          "finite:", round(float(np.isfinite(out).mean()), 4))

read_range(8187, 8278, "/work/parts/tgt.npy")
