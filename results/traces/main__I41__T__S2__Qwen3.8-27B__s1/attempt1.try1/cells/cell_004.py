import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds['analysed_sst']
print("encoding:", v.encoding)
print("time attrs:", ds['time'].attrs)
t = ds.time.values
print("first/last:", t[0], t[-1])
# check continuity
import pandas as pd
td = pd.to_datetime(t)
diffs = np.diff(td)
print("unique diffs:", set(diffs.astype('timedelta64[D]').astype(int)))
print("any dup:", (diffs==0).any())
