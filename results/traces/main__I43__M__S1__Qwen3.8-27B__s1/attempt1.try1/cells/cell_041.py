import xarray as xr, json, numpy as np, os
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
m = ds["mhw"]
print("mhw dtype:", m.dtype, "dims:", m.dims)
print("shape:", m.shape, "sum:", int(m.values.sum()), "min/max:", int(m.values.min()), int(m.values.max()))
print("time[0]:", ds.time.values[0], "time[-1]:", ds.time.values[-1])
print("lat[0]:", float(ds.lat.values[0]), "lat[-1]:", float(ds.lat.values[-1]), "n:", ds.lat.size)
print("lon[0]:", float(ds.lon.values[0]), "lon[-1]:", float(ds.lon.values[-1]), "n:", ds.lon.size)
# confirm coords match the source dataset's values
src = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20170701.nc", engine="h5netcdf")
slat = (src.latitude.values.astype("float64")>=62.25-1e-9)&(src.latitude.values.astype("float64")<=63.45+1e-9)
slon = (src.longitude.values.astype("float64")>=18.73-1e-9)&(src.longitude.values.astype("float64")<=19.93+1e-9)
print("lat match:", bool(np.array_equal(ds.lat.values.astype("float64"), src.latitude.values.astype("float64")[slat])))
print("lon match:", bool(np.array_equal(ds.lon.values.astype("float64"), src.longitude.values.astype("float64")[slon])))
src.close()
rep = json.load(open("output/report.json"))
print("report keys:", sorted(rep.keys()))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(rep["region"].keys()) == {"lat_min","lat_max","lon_min","lon_max"}
assert rep["complete"] is True and isinstance(rep["caveats"], str) and isinstance(rep["events"], list)
print("report OK:", rep)
print("file sizes:", os.path.getsize("output/mhw_mask.nc"), os.path.getsize("output/report.json"))
