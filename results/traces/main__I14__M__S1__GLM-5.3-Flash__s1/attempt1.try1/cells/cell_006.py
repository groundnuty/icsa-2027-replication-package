import os, time, xarray as xr, numpy as np, datetime as dt
d = "/data/icsa2027_data_20261101T090944Z/s1z"
try:
    import dask; print("dask:", dask.__version__)
except Exception as e:
    print("no dask:", e); raise SystemExit

sl = dict(latitude=slice(132,192), longitude=slice(436,496))
dates = []
cur = dt.date(1991,12,27)
while cur <= dt.date(2003,1,5):
    dates.append(cur); cur += dt.timedelta(days=1)

t0 = time.time()
paths = [os.path.join(d, f"sst_{c:%Y%m%d}.nc") for c in dates]
ds = xr.open_mfdataset(paths, engine="h5netcdf", combine="nested", concat_dim="time",
                       parallel=True, preprocess=lambda x: x[["analysed_sst"]].isel(time=0).expand_dims("time").isel(**sl))
print("open_mfdataset setup: %.2f s" % (time.time()-t0), ds)
