import xarray as xr, time
base = "/data/icsa2027_data_20261101T090944Z/s1z"
p = base + "/sst_20210601.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds['analysed_sst'].attrs)
print("encoding:", ds['analysed_sst'].encoding)
t0 = time.time()
v = ds['analysed_sst'].values
print("full read time:", time.time()-t0)
import numpy as np
print("dtype", v.dtype, "min/max finite:", np.nanmin(v), np.nanmax(v))
print("n NaN:", np.isnan(v).sum())
# region slice read benchmark
t0 = time.time()
s = ds['analysed_sst'].isel(latitude=slice(48,108), longitude=slice(353,413)).values
print("slice read time:", time.time()-t0, s.shape)
print("lat coords:", ds['latitude'].values[46:50], ds['latitude'].values[106:110])
print("lon coords:", ds['longitude'].values[351:355], ds['longitude'].values[410:414])
print("slice min/max:", np.nanmin(s), np.nanmax(s), "NaN:", np.isnan(s).sum())
ds.close()
