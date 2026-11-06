import numpy as np, pandas as pd, json, os
import xarray as xr
os.makedirs("output", exist_ok=True)

zt = np.load("work/target.npz")
mhw = np.load("work/mhw.npy")          # (92, 60, 60) uint8
ev = json.load(open("work/events.json"))

ds = xr.Dataset(
    data_vars={"mhw": (("time", "latitude", "longitude"), mhw.astype(np.uint8))},
    coords={
        "time": ("time", zt["time"]),
        "latitude": ("latitude", zt["lat"].astype(np.float32)),
        "longitude": ("longitude", zt["lon"].astype(np.float32)),
    },
)
ds["latitude"].attrs = {"units": "degrees_north", "standard_name": "latitude", "long_name": "Latitude"}
ds["longitude"].attrs = {"units": "degrees_east", "standard_name": "longitude", "long_name": "Longitude"}
ds["time"].attrs = {"standard_name": "time", "axis": "T", "long_name": "Time"}
ds.attrs = {"title": "Per-cell MHW membership, Baltic Sea region 61.57-62.77N 20.17-21.37E, 2021-06-01..2021-08-31",
            "source_dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
            "comment": "mhw=1 where the cell is inside a per-cell MHW on that day, 0 otherwise (land cells 0)."}
ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": 61.57, "lat_max": 62.77, "lon_min": 20.17, "lon_max": 21.37},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": e[0], "end": e[1]} for e in ev["events"]],
    "complete": True,
    "caveats": "292 of the 3600 regional grid cells have no finite SST on any target day (land) and are set to 0; the remaining 3308 sea cells were fully used.",
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("written")
print(json.dumps(report, indent=1))
