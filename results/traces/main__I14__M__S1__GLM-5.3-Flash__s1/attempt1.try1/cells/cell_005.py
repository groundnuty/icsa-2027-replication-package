import os, time, xarray as xr, numpy as np, datetime as dt
d = "/data/icsa2027_data_20261101T090944Z/s1z"

# time a few reads of the region slice
t0 = time.time()
for fn in ["sst_19920101.nc","sst_19920601.nc","sst_19950228.nc","sst_20000615.nc","sst_20030605.nc","sst_20150601.nc"]:
    ds = xr.open_dataset(os.path.join(d, fn), engine="h5netcdf")
    v = ds["analysed_sst"].isel(time=0, latitude=slice(132,192), longitude=slice(436,496)).values
    ds.close()
print("6 reads, %.3f s" % (time.time()-t0), v.shape, v.dtype)

# check one file's region: NaN fraction, value range
print("finite frac:", np.isfinite(v).mean(), "min/max:", np.nanmin(v), np.nanmax(v))

# verify time coordinate matches filename for a few random files
import random
random.seed(0)
ok = True
for fn in random.sample([f for f in os.listdir(d)], 12):
    ds = xr.open_dataset(os.path.join(d, fn), engine="h5netcdf")
    tv = ds["time"].values[0]
    ds.close()
    expect = np.datetime64(dt.datetime.strptime(fn[4:12], "%Y%m%d"))
    if tv != expect: ok = False; print("MISMATCH", fn, tv)
print("time matches filename (12 random):", ok)
