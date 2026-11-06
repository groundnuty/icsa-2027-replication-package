import h5py, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20120615.nc"
with h5py.File(p, "r") as f:
    tv = f["time"]
    print("time attrs:", dict(tv.attrs))
    print("time value:", tv[:])
    print("lat dtype/shape:", f["latitude"].dtype, f["latitude"].shape)
import xarray as xr
ds = xr.open_dataset(p, engine="h5netcdf")
print("decoded time:", ds.time.values)
# try to reproduce decoding manually
raw = 991353600
# guess units from attrs
