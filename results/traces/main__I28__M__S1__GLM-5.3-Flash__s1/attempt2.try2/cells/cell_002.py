import os, xarray as xr, numpy as np
base = "/data/icsa2027_data_20261101T090944Z/s1z"
names = sorted(os.listdir(base))
print("first:", names[0], "last:", names[-1], "count:", len(names))
# check naming pattern consistency
import re
pat = re.compile(r"^sst_(\d{8})\.nc$")
bad = [n for n in names if not pat.match(n)]
print("bad names:", bad[:5], len(bad))
ds = xr.open_dataset(os.path.join(base, "sst_20130601.nc"), engine="h5netcdf")
print(ds)
print("\nattrs:", ds.attrs)
