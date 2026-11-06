import numpy as np, xarray as xr, time
print("numpy", np.__version__)
print("xarray", xr.__version__)
try:
    print(np.nanquantile([1.,2.,3.,4.], 0.9, method="hazen"))
except Exception as e:
    print("hazen not available:", e)
import h5netcdf
print("h5netcdf", h5netcdf.__version__)

base = "/data/icsa2027_data_20261101T090944Z/s1z"
t0 = time.time()
ds = xr.open_dataset(f"{base}/sst_20120601.nc", engine="h5netcdf")
t1 = time.time()
v = ds.analysed_sst[0, 48:108, 353:413].values.astype(np.float64)
t2 = time.time()
print("open:", t1-t0, "read slice:", t2-t1)
print(v.shape, np.isfinite(v).sum())
# check time coordinate value
print(ds.time.values, ds.time.attrs)
ds.close()
t0 = time.time()
ds = xr.open_dataset(f"{base}/sst_20120601.nc", engine="h5netcdf")
v2 = ds.analysed_sst[0, 48:108, 353:413].values
print("2nd open+read:", time.time()-t0)
ds.close()
