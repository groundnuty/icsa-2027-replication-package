import numpy as np, pickle, json, os
import xarray as xr

with open('/tmp/stepA2.pkl','rb') as fh: A = pickle.load(fh)
with open('/tmp/stepB2.pkl','rb') as fh: B = pickle.load(fh)
mhw = B['mhw']; tdates = B['tdates']
latvals, lonvals = A['latvals'], A['lonvals']

os.makedirs('output', exist_ok=True)
print("cwd:", os.getcwd())

ds = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw.astype(np.uint8))},
    coords={"time": tdates.values, "lat": latvals.astype(np.float32), "lon": lonvals.astype(np.float32)},
)
ds["mhw"].attrs = {"long_name": "per-cell marine heatwave mask (1 = cell inside MHW that day)", "flag_values": [0, 1], "flag_meanings": "not_in_mhw in_mhw"}
ds.attrs["title"] = "Baltic Sea MHW per-cell mask, 2015-06-01..2015-08-31, region 56.13-57.33N 17.71-18.91E"
ds.attrs["source_dataset"] = "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m"
ds.attrs["baseline"] = "1992-2002 pools (+/-5 calendar days, incl. 1991-12-27..31 and 2003-01-01..05 shoulders); 90th percentile (Hazen/type 5); day 60 = mean of days 59 and 61; wrapped 31-day moving mean"
try:
    ds.to_netcdf('output/mhw_mask.nc', engine='netcdf4')
    print("written with netcdf4 engine")
except Exception as e:
    print("netcdf4 failed:", e)
    ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
    print("written with h5netcdf engine")

report = {
    "region": {"lat_min": 56.13, "lat_max": 57.33, "lon_min": 17.71, "lon_max": 18.91},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2015-06-01", "end": "2015-08-31"},
    "events": B['ev'],
    "complete": True,
    "caveats": ("Baseline pools use exact calendar windows of +/-5 days around each day-of-year, including the "
                "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 shoulder days exactly as specified; 29 February "
                "values enter the pools of their calendar neighbours. Day 60 of the climatology/threshold is the "
                "mean of days 59 and 61 before smoothing. All comparisons done in float64 on stored kelvin values. "
                "An alternative day-of-year-window reading of the pooling rule changes thresholds only at winter/"
                "leap-seam doys (1-10, 55-65, 357-366), far from the June-August target band, and yields a "
                "bitwise-identical MHW mask and the same single regional event.")
}
with open('output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print("report written")
print(json.dumps(report, indent=1)[:1200])
