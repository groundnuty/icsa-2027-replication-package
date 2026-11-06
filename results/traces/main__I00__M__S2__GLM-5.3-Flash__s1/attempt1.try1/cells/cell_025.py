import json, numpy as np, xarray as xr, os

print("cwd:", os.getcwd(), "| files:", sorted(os.listdir("output")))
# validate report.json
rep = json.load(open("output/report.json"))
expected_keys = {"region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"}
print("report keys exact:", set(rep.keys()) == expected_keys)
print("region:", rep["region"])
print("baseline_analysed:", rep["baseline_analysed"])
print("target_analysed:", rep["target_analysed"])
print("events:", rep["events"], "| complete:", rep["complete"])

# validate mhw_mask.nc
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print("\nmhw_mask.nc dims:", dict(ds.sizes))
print("vars:", list(ds.variables))
print("mhw dtype:", ds.mhw.dtype, "| time dtype:", ds.time.dtype)
print("time first/last:", str(ds.time.values[0])[:10], str(ds.time.values[-1])[:10], "n =", ds.sizes["time"])
print("lat first/last:", ds.lat.values[0], ds.lat.values[-1], "n =", ds.sizes["lat"])
print("lon first/last:", ds.lon.values[0], ds.lon.values[-1], "n =", ds.sizes["lon"])
mv = ds.mhw.values
print("mhw unique values:", np.unique(mv), "| dtype:", mv.dtype)
# compare against computed mask
ref = np.load("/tmp/mhw_work/mhw_mask.npy")
print("matches computed mask exactly:", bool((mv.astype(bool) == ref).all()))
# coordinate values match dataset
ds0 = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
lat0 = ds0.latitude.values; lon0 = ds0.longitude.values
lat_sel = np.where((lat0 >= 54.13) & (lat0 <= 55.33))[0]
lon_sel = np.where((lon0 >= 14.67) & (lon0 <= 15.87))[0]
print("lat coords identical to dataset:", bool((ds.lat.values.astype('float64') == lat0[lat_sel].astype('float64')).all()))
print("lon coords identical to dataset:", bool((ds.lon.values.astype('float64') == lon0[lon_sel].astype('float64')).all()))
t0 = ds0.time.values
print("time coords identical to dataset:", bool((ds.time.values == t0[[i for i in range(len(t0)) if "2004-06-01" <= str(t0[i])[:10] <= "2004-08-31"]]).all()))
