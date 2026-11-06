import xarray as xr, json, numpy as np
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
v = ds["mhw"]
print("dtype:", v.dtype, "dims:", dict(v.sizes))
print("values: min", int(v.min()), "max", int(v.max()), "sum", int(v.sum()))
print("time[0], time[-1]:", ds["time"].values[0], ds["time"].values[-1])
print("lat range:", float(ds["lat"].values[0]), float(ds["lat"].values[-1]))
print("lon range:", float(ds["lon"].values[0]), float(ds["lon"].values[-1]))
print("lat n:", len(ds["lat"]), "lon n:", len(ds["lon"]), "time n:", len(ds["time"]))
r = json.load(open("output/report.json"))
print("report keys:", list(r.keys()))
print("events:", r["events"], "complete:", r["complete"])
