import h5py, time, numpy as np
base = "/data/icsa2027_data_20261101T090944Z/s1z"
p = f"{base}/sst_20120701.nc"
f = h5py.File(p, "r")
v = f['analysed_sst']
a_full = v[0][:][330:390, 551:611]
f.close()
import xarray as xr
ds = xr.open_dataset(p, engine="h5netcdf", decode_times=False)
a_xr = ds['analysed_sst'].sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21)).values[0]
ds.close()
print("equal_nan:", np.array_equal(a_xr, a_full, equal_nan=True))
