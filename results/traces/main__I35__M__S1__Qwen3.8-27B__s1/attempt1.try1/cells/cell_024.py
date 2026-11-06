import numpy as np, json, datetime as dt, os
import xarray as xr

os.makedirs("output", exist_ok=True)
raw = json.load(open("/tmp/mhw/dates.json"))
target = [dt.date.fromisoformat(x) for x in raw["target"]]
inmhw = np.load("/tmp/mhw/inmhw.npy")
lat = np.load("/tmp/mhw/lat.npy")
lon = np.load("/tmp/mhw/lon.npy")

mhw3 = inmhw.reshape(92, 60, 60)
print("mask ones:", int(mhw3.sum()), "dtype check:", inmhw.dtype)

ds = xr.Dataset(
    {"mhw": xr.DataArray(mhw3.astype(np.uint8), dims=("time", "lat", "lon"),
                          coords={"time": np.array(target, dtype="datetime64[ns]"),
                                  "lat": lat.astype(np.float32),
                                  "lon": lon.astype(np.float32)})}
)
ds.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")
print(ds)

events = [{"onset": "2009-06-26", "end": "2009-07-07"},
          {"onset": "2009-08-06", "end": "2009-08-10"}]
report = {
    "region": {"lat_min": 59.93, "lat_max": 61.13, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
    "events": events,
    "complete": True,
    "caveats": ""
}
json.dump(report, open("output/report.json", "w"), indent=2)
print(json.dumps(report, indent=2))
