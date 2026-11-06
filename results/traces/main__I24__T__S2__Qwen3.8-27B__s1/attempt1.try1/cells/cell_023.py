import numpy as np, xarray as xr, json, os

sub = xr.open_dataset("/tmp/mhw/subset.nc")
ts = sub.time.values.astype("datetime64[D]")
mask = np.load("/tmp/mhw/mask.npy")   # (92, 60, 60) uint8
sea  = np.load("/tmp/mhw/sea.npy")

T0 = 4028
tt_times = ts[T0:]

os.makedirs("output", exist_ok=True)
out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mask.astype(np.uint8))},
    coords={
        "time": ("time", sub.time[T0:].values),
        "lat":  ("lat",  sub.latitude.values.astype(np.float32)),
        "lon":  ("lon",  sub.longitude.values.astype(np.float32)),
    },
)
out["mhw"].attrs = {"long_name": "per-cell marine heatwave mask (1 = inside per-cell MHW, 0 otherwise; land 0)",
                    "flag_values": [0, 1], "flag_meanings": ["not in MHW", "in MHW"]}
out.to_netcdf("output/mhw_mask.nc")

events = [{"onset": "2004-08-05", "end": "2004-08-15"}]
report = {
    "region": {"lat_min": 57.57, "lat_max": 58.77, "lon_min": 10.25, "lon_max": 11.45},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("Region covered by 60x60 cells of the dataset's 0.02-deg grid (lat 57.58-58.76 N, lon 10.26-11.44 E; "
                "requested bounds fall between grid points, so nearest grid cells were included). "
                "296 of 3600 region cells have no SST on any target day (and none in the baseline either; land/no-data) "
                "and are set to 0; the remaining 3304 sea cells (finite SST on all 92 target days) were used. "
                "Thresholds/climatology from 1992-2002 baseline pools of +/-5 calendar days (extending to 1991-12-27..31 "
                "and 2003-01-01..05), day 60 = mean of days 59/61, then 31-day centred circular smoothing; "
                "per-cell MHWs: >=5 consecutive days with SST(kelvin) >= smoothed day-of-year threshold, gaps of <=2 days merged. "
                "One regional event was found: 2004-08-05 to 2004-08-15 (all 2356 MHW cells active 2004-08-10/11)."),
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

# ---- validation ----
chk = xr.open_dataset("output/mhw_mask.nc")
print(chk)
m = chk.mhw.values
print("dtype:", m.dtype, "shape:", m.shape)
print("time:", chk.time.values[0], "->", chk.time.values[-1], "n=", len(chk.time))
print("lat:", chk.lat.values[0], chk.lat.values[-1], "lon:", chk.lon.values[0], chk.lon.values[-1])
print("mhw value counts:", {int(v): int((m == v).sum()) for v in np.unique(m)})
# consistency: mask equals saved; land cells zero
assert m.dtype == np.uint8
assert np.array_equal(m, mask)
assert not m[:, ~sea].any()
# event consistency re-derived from the written file
act = m.any(axis=2).any(axis=1)
pad = np.concatenate(([False], act, [False]))
d = np.diff(pad.astype(np.int8))
ev = [(str(chk.time.values[s].astype('datetime64[D]')), str(chk.time.values[e].astype('datetime64[D]')))
      for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1)]
print("events from written file:", ev)
assert ev == [("2004-08-05", "2004-08-15")]
print(json.dumps(report, indent=2)[:600])
print("FILES WRITTEN OK")
