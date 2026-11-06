import xarray as xr, numpy as np, json, h5py
out = xr.open_dataset("output/mhw_mask.nc")
src = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc", engine="h5netcdf")
print("mhw dtype:", out.mhw.dtype, "dims:", out.mhw.dims)
print("nones:", out.mhw.isel(time=0).values.sum(), "| total ones:", int(out.mhw.values.sum()), "(expect 4296)")
print("time matches src:", np.array_equal(out.time.values, src.sel(time="2008-06-01").time.values))
lat_ok = np.array_equal(out.lat.values, src.latitude.sel(latitude=slice(56.63,57.83)).values)
lon_ok = np.array_equal(out.lon.values, src.longitude.sel(longitude=slice(20.23,21.43)).values)
print("lat coords match dataset:", lat_ok, "| lon coords match dataset:", lon_ok)
print("lat:", out.lat.values[0], out.lat.values[-1], "| lon:", out.lon.values[0], out.lon.values[-1])
# land cells must be 0
ocean = np.load("/tmp/ocean.npy").reshape(60,60)
land_ones = int(out.mhw.values[:, ~ocean.ravel()].sum())
print("ones on land cells:", land_ones, "(expect 0)")
# active days in file match events
perday = out.mhw.values.sum(axis=(1,2))
active_days = [out.time.values[i].astype("datetime64[D]").astype(str) for i in np.nonzero(perday)[0]]
print("active days in file:", active_days)
rep = json.load(open("output/report.json"))
print("report fields:", list(rep.keys()))
print("events:", rep["events"], "| complete:", rep["complete"])
print("ALL CHECKS DONE")
