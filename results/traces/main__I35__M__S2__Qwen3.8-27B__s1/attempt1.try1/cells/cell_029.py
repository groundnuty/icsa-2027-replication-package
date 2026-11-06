import numpy as np, json, os
import xarray as xr

os.makedirs("~", exist_ok=True)
os.makedirs("output", exist_ok=True)

mhw_flat = np.load("/tmp/final_mhw.npy")          # (92, 3302) uint8
sea = np.load("/tmp/sea.npy")                     # (60, 60)
events = json.load(open("/tmp/final_events.json"))

lat_idx, lon_idx = np.where(sea)
assert len(lat_idx) == mhw_flat.shape[1]
mhw3d = np.zeros((92, 60, 60), dtype=np.uint8)
mhw3d[:, lat_idx, lon_idx] = mhw_flat
print("mhw3d sum:", int(mhw3d.sum()), "flat sum:", int(mhw_flat.sum()))

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat_vals = ds.latitude.values[322:382]
lon_vals = ds.longitude.values[485:545]
t = ds.time.values
i0 = int(np.searchsorted(t, np.datetime64("2009-06-01")))
time_vals = t[i0:i0+92]
assert str(time_vals[0])[:10] == "2009-06-01" and str(time_vals[-1])[:10] == "2009-08-31" and len(time_vals) == 92
ds.close()
print("lat:", lat_vals[0], lat_vals[-1], " lon:", lon_vals[0], lon_vals[-1])

attrs = {"description": "1 where the grid cell is inside a per-cell MHW on that day, 0 otherwise (land cells 0)",
         "long_name": "marine heatwave mask"}
out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw3d, attrs)},
    coords={"time": ("time", time_vals), "lat": ("lat", lat_vals), "lon": ("lon", lon_vals)}
)
out.to_netcdf("~/mhw_mask.nc")
out.to_netcdf("output/mhw_mask.nc")
print("wrote mhw_mask.nc")

report = {
    "region": {"lat_min": 59.93, "lat_max": 61.13, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
    "events": events,
    "complete": True,
    "caveats": (
        "Region spans 3600 grid cells (lat 59.94-61.12 N, lon 18.70-19.88 E on the dataset grid); "
        "3302 cells with finite SST on all 92 target days were used as sea cells, 298 land cells excluded (0 in the mask). "
        "Per-day-of-year pools use the 1992-2002 baseline with +/-5-day windows; per the method, the end windows also use "
        "1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05. Threshold = 90th percentile (Hazen type-5), climatology = mean, "
        "NaN ignored; day of year 60 set to the mean of 59 and 61; both smoothed with a 31-day centred wrap-around moving mean. "
        "SST compared in kelvin as stored. Hot days >= smoothed threshold; per-cell MHW = run of >=5 consecutive hot days, "
        "with runs separated by 1-2 non-hot days joined (gap days included). 2 regional events found; 17 active days of 92."
    )
}
with open("~/report.json", "w") as f: json.dump(report, f, indent=2)
with open("output/report.json", "w") as f: json.dump(report, f, indent=2)
print("wrote report.json")
print(json.dumps(events))
