import numpy as np, fsspec, xarray as xr, time, os

t0c = time.time()
fs = fsspec.filesystem('onedata')
f = fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

os.makedirs("work", exist_ok=True)
i0, i1 = 3647, 7674   # 1991-12-27 .. 2003-01-05
B = 500
for s in range(i0, i1 + 1, B):
    e = min(s + B - 1, i1)
    fn = f"work/base_{s}.npy"
    if os.path.exists(fn):
        continue
    if time.time() - t0c > 120:
        print("budget stop before batch", s)
        break
    a = ds.analysed_sst.isel(time=slice(s, e + 1),
                             latitude=slice(109, 169),
                             longitude=slice(373, 433)).values
    np.save(fn, a.astype(np.float32))
    print("saved batch", s, "-", e, a.shape, "%.1fs" % (time.time() - t0c), flush=True)

if not os.path.exists("work/tgt.npy"):
    a = ds.analysed_sst.isel(time=slice(8552, 8644),
                             latitude=slice(109, 169),
                             longitude=slice(373, 433)).values
    np.save("work/tgt.npy", a.astype(np.float32))
    print("target saved", a.shape, flush=True)

import pandas as pd
tb = pd.to_datetime(ds.time.values[3647:7675])
tt = pd.to_datetime(ds.time.values[8552:8644])
assert str(tb[0].date()) == "1991-12-27" and str(tb[-1].date()) == "2003-01-05"
assert str(tt[0].date()) == "2005-06-01" and str(tt[-1].date()) == "2005-08-31"
np.savez("work/coords.npz",
         lat=ds.latitude.values[109:169], lon=ds.longitude.values[373:433],
         t_base=ds.time.values[3647:7675], t_tgt=ds.time.values[8552:8644])
print("coords saved")

remaining = [s for s in range(i0, i1 + 1, B) if not os.path.exists(f"work/base_{s}.npy")]
print("remaining batches:", remaining)
print("total elapsed %.1fs" % (time.time() - t0c))
