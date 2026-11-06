import numpy as np, json, os, xarray as xr

os.makedirs("output", exist_ok=True)
mhw = np.load("/tmp/mhw_mask.npy")                 # (92, 60, 60) bool
alldays = open("/tmp/alldays.txt").read().split("\n")
target_days = alldays[4028:]
nt = len(target_days)
assert mhw.shape == (nt, 60, 60)

# fetch exact coordinate values from the dataset
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat_all = ds["latitude"].values; lon_all = ds["longitude"].values; time_all = ds["time"].values
lati = np.where((lat_all >= 63.31) & (lat_all <= 64.51))[0]
loni = np.where((lon_all >= 21.31) & (lon_all <= 22.51))[0]
lat_v = lat_all[lati]; lon_v = lon_all[loni]
tmask = (time_all >= np.datetime64("2004-06-01")) & (time_all <= np.datetime64("2004-08-31"))
time_v = time_all[tmask]
assert len(time_v) == nt and [str(t)[:10] for t in time_v] == target_days
ds.close()

out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw.astype(np.uint8))},
    coords={"time": time_v, "lat": lat_v, "lon": lon_v},
)
out["mhw"].attrs = {"long_name": "marine heatwave (per-cell) mask", "flag_values": [0, 1],
                    "flag_meanings": "not_in_mhw in_mhw"}
out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")

report = {
    "region": {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": [{"onset": "2004-08-07", "end": "2004-08-12"}],
    "complete": True,
    "caveats": ("Sea cells: 3299 of 3600 (finite SST on every target day). Baseline pools are the "
                "+-5-calendar-day windows around each 1992-01-01..2002-12-31 anchor date of a given "
                "day of year, so they include the halo days 1991-12-27..1991-12-31 and "
                "2003-01-01..2003-01-05 (121 values per pool for every sea cell); day 60 (29 Feb) "
                "was set to the mean of days 59 and 61 before smoothing. Hot runs of >=5 days were "
                "identified first and only then joined across 1-2 non-hot day gaps; no such gap "
                "occurred in this period, so no joining was needed. No SST value exactly equalled "
                "its threshold."),
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("written:", os.listdir("output"))
print(json.dumps(report, indent=2)[:1200])
