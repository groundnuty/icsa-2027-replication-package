import numpy as np, os, json, xarray as xr
st2 = np.load("cache/stage2.npz")
st1 = np.load("cache/stage1.npz")
d = np.load("cache/region.npz")
mhw = st2['mhw']                      # (92, nsea)
nsea_all = st1['nsea_all']            # (3600,)
lat, lon = d['lat'], d['lon']
tt = d['time_tgt']                    # str
events = st2['events']

mask_full = np.zeros((92, 60, 60), dtype=np.uint8)
mask_full[:, nsea_all.reshape(60, 60)] = mhw
print("mask_full nonzeros:", int(mask_full.sum()), "sea cells with MHW:", int((mask_full.sum(0) > 0).sum()))

os.makedirs("output", exist_ok=True)
time64 = np.array(tt, dtype="datetime64[ns]")
ds_out = xr.Dataset(
    {"mhw": xr.DataArray(mask_full, dims=("time", "latitude", "longitude"),
                         attrs={"description": "1 where the cell is inside a per-cell MHW on that day (0 otherwise; land cells 0)"})},
    coords={"time": ("time", time64),
            "latitude": ("latitude", lat),
            "longitude": ("longitude", lon)})
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": 54.81, "lat_max": 56.01, "lon_min": 19.61, "lon_max": 20.81},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2022-06-01", "end": "2022-08-31"},
    "events": [{"onset": str(tt[s])[:10], "end": str(tt[e])[:10]} for s, e in events],
    "complete": True,
    "caveats": ("311 of 3600 region grid cells had missing SST on some target day and were excluded (not sea cells). "
                "The 90th-percentile threshold uses numpy method='hazen' (Hyndman-Fan type 5) per the task; "
                "the final event ends at the last analysed day (2022-08-31), so it may continue beyond the target period.")
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))