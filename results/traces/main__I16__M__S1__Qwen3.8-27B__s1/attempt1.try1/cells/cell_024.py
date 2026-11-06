import xarray as xr, numpy as np
out = xr.open_dataset("output/mhw_mask.nc")
src = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc", engine="h5netcdf")
print("src time raw:", src.time.values, src.time.dtype, "units:", src.time.attrs.get("units"))
print("out time raw:", out.time.values[:3], out.time.dtype, out.time.attrs)
print("equal day-wise:", np.array_equal(out.time.values.astype("datetime64[D]"), src.time.values.astype("datetime64[D]")))

ocean = np.load("/tmp/ocean.npy").reshape(60,60)
print("ones on land cells:", int(out.mhw.values.reshape(92,3600)[:, ~ocean.ravel()].sum()), "(expect 0)")
perday = out.mhw.values.sum(axis=(1,2))
print("active days in file:", [str(out.time.values[i].astype("datetime64[D]")) for i in np.nonzero(perday)[0]])
print("per-day counts:", [int(x) for x in perday if x>0])
