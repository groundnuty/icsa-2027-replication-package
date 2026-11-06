import fsspec, xarray as xr, numpy as np, time, os
t0 = time.time()
fs = fsspec.filesystem('onedata')
p = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

sel = dict(latitude=ds.latitude[np.arange(204,264)], longitude=ds.longitude[np.arange(63,123)])
tb = ds.analysed_sst.sel(time=slice("1991-12-27","2003-01-05"), **sel).load()
tt = ds.analysed_sst.sel(time=slice("2004-06-01","2004-08-31"), **sel).load()
print("reads done", time.time()-t0)

times = np.concatenate([tb.time.values, tt.time.values])
vals  = np.concatenate([tb.values, tt.values], axis=0).astype(np.float64)
da = xr.DataArray(vals, dims=("time","latitude","longitude"),
                  coords={"time": times, "latitude": tb.latitude.values, "longitude": tb.longitude.values},
                  name="analysed_sst")
da.attrs["units"] = "kelvin"
os.makedirs("/tmp/mhw", exist_ok=True)
da.to_dataset().to_netcdf("/tmp/mhw/subset.nc")
print("saved", time.time()-t0, "days:", len(times))
seg1 = times[:4028]; seg2 = times[4028:]
print("seg1:", seg1[0], "->", seg1[-1], "n=", len(seg1), "gaps:", (np.diff(seg1).astype("timedelta64[D]") != 1).sum())
print("seg2:", seg2[0], "->", seg2[-1], "n=", len(seg2), "gaps:", (np.diff(seg2).astype("timedelta64[D]") != 1).sum())
print("finite frac baseline:", np.isfinite(vals[:4028]).mean(), "target:", np.isfinite(vals[4028:]).mean())
ds.close(); f.close()
