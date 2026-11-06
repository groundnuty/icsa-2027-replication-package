
import os, json, pickle, warnings
import numpy as np, xarray as xr
warnings.filterwarnings("ignore")
print("cwd:", os.getcwd())
os.makedirs("output", exist_ok=True)

dates = pickle.load(open("/work/dates.pkl","rb"))
tgt = dates["target"]; nT = len(tgt)
percell = np.load("/work/percell.npy")           # (92, 3600) bool
lat_r = np.load("/work/lat_r.npy")               # (60,) float32
lon_r = np.load("/work/lon_r.npy")               # (60,) float32
saved = pickle.load(open("/work/events.pkl","rb"))

mhw = percell.reshape(nT, 60, 60).astype(np.uint8)
print("mask shape:", mhw.shape, "dtype uint8; sum:", int(mhw.sum()), "per-day max:", int(mhw.max(axis=(1,2)).max()))

time_vals = np.array(tgt, dtype="datetime64[ns]")
da = xr.DataArray(
    mhw,
    dims=("time", "lat", "lon"),
    coords={"time": time_vals, "lat": lat_r, "lon": lon_r},
    name="mhw",
)
da.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": 55.67, "lat_max": 56.87, "lon_min": 16.45, "lon_max": 17.65},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": a, "end": b} for a, b in saved["events"]],
    "complete": True,
    "caveats": ("All 4120 required daily files (1991-12-27 to 2003-01-05 for the threshold/climatology "
                "pools and 2021-06-01 to 2021-08-31 target period) were present and read successfully. "
                "3310 of the 3600 region grid cells are sea cells (finite SST on every target day); the "
                "remaining 290 land cells are excluded from MHW detection and reported as 0. "
                "Thresholds use the Hazen (Hyndman-Fan type 5) 90th percentile of each day-of-year pool; "
                "day 60 values were set to the mean of days 59 and 61 and both fields were smoothed with a "
                "31-day centred wrap-around moving mean."),
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("files written:", os.listdir("output"))
print(json.dumps(report, indent=2)[:600])
