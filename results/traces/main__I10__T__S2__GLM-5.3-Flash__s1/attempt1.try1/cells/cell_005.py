import time, fsspec, xarray as xr, numpy as np

fs = fsspec.filesystem('onedata')
f = fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

t0 = time.time()
for i in [3647, 4000, 5000, 6000, 7000]:
    a = ds.analysed_sst.isel(time=i, latitude=slice(109,169), longitude=slice(373,432)).values
    print(i, a.shape, float(np.nanmean(a)), "nanfrac", float(np.mean(~np.isfinite(a))))
dt = time.time() - t0
print("elapsed for 5 steps: %.2f s -> %.2f s/step" % (dt, dt/5))
