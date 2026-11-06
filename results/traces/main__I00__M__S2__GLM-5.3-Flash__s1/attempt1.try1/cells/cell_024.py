script = r'''
import numpy as np, pickle, json, os
import xarray as xr

meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
lat_vals = meta["lat_vals"]          # float64, 60 values
lon_vals = meta["lon_vals"]
target_md = meta["target_md"]

targ_dates = [np.datetime64("2004-%02d-%02d" % (m, d)) for (m, d) in target_md]
mhw_mask = np.load("/tmp/mhw_work/mhw_mask.npy")   # (92, 60, 60) bool
assert mhw_mask.shape == (len(targ_dates), len(lat_vals), len(lon_vals))

mhw = mhw_mask.astype("uint8")
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw, {"long_name": "per-cell marine heatwave mask",
                                            "flag_values": np.array([0, 1], dtype="uint8"),
                                            "flag_meanings": "not_in_mhw in_mhw"})},
    coords={"time": ("time", targ_dates, {"long_name": "Time", "standard_name": "time"}),
            "lat": ("lat", lat_vals, {"units": "degrees_north", "standard_name": "latitude"}),
            "lon": ("lon", lon_vals, {"units": "degrees_east", "standard_name": "longitude"})},
)
ds_out["mhw"].encoding = {"dtype": "uint8"}

os.makedirs("output", exist_ok=True)
ds_out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": [],
    "complete": True,
    "caveats": ("No regional marine heatwave events were found in this region for 2004-06-01 to 2004-08-31: "
                "in every sea cell the summer-2004 SST stayed below the cell's smoothed 90th-percentile "
                "threshold except for 6 isolated cell-days (3 days) with exceedances of at most +0.14 K, "
                "so no run reached the 5-day minimum duration even before gap joining. "
                "Baseline pools additionally use days just outside the nominal baseline "
                "(1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05), as required by the method; "
                "they are reflected in baseline_analysed. Thresholds, climatology, smoothing and "
                "comparisons were computed in float64; SST was read as stored (kelvin, float32 source "
                "data cast to float64)."
               ),
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")
print(json.dumps({k: (v if k != "caveats" else v[:80] + "...") for k, v in report.items()}, indent=1))
'''
open("/tmp/mhw_work/write_out.py", "w").write(script)
exec(open("/tmp/mhw_work/write_out.py").read())
