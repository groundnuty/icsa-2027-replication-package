import xarray as xr, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
import os
base = "/data/icsa2027_data_20261101T090944Z/s1z"

def load_one(fname, i0=204, i1=264, j0=63, j1=123):
    p = os.path.join(base, fname)
    ds = xr.open_dataset(p, engine="h5netcdf")
    try:
        a = ds["analysed_sst"].values[0, i0:i1, j0:j1].astype(np.float64)
        return fname, a
    finally:
        ds.close()

test_files = [f"sst_{d}.nc" for d in ["20040601","20040615","20040715","20040815","20040602","20040603","20040604","20040605","20040606","20040607","20040608","20040609","20040610","20040611","20040612","20040613","20040614","20040616","20040617","20040618","20040619","20040620","20040621","20040622"]]
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(lambda f: load_one(f), test_files))
t1 = time.time()
print(f"{len(res)} files in {t1-t0:.1f}s -> {(t1-t0)/len(res)*1000:.0f} ms/file (8 threads)")
print("shape:", res[0][1].shape, "finite frac:", np.isfinite(res[0][1]).mean())
