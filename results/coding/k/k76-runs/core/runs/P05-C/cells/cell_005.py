import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
T_START = dt.date(2003, 6, 1)
T_END = dt.date(2003, 8, 31)
TOL = 1e-4

meta = json.load(open("meta.json"))
tdays = [dt.date.fromisoformat(s) for s in meta["days"]]
lat = np.load("lat.npy"); lon = np.load("lon.npy")

mask_s = np.load("mask_s.npy")
sea_idx = np.load("sea_idx.npy")
full = np.zeros((len(tdays), len(lat) * len(lon)), dtype=np.uint8)
full[:, sea_idx] = mask_s
full = full.reshape(len(tdays), len(lat), len(lon))

os.makedirs("output", exist_ok=True)
out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), full.astype(np.uint8))},
    coords={"time": np.array(tdays, dtype="datetime64[ns]"), "lat": lat, "lon": lon},
)
out.to_netcdf("output/mhw_mask.nc")
print("wrote output/mhw_mask.nc", full.shape, "flagged", int(full.sum()))

active = full.any(axis=(1, 2))
events = []
k = 0
while k < len(active):
    if active[k]:
        j = k
        while j + 1 < len(active) and active[j + 1]:
            j += 1
        events.append({"onset": tdays[k].isoformat(), "end": tdays[j].isoformat()})
        k = j + 1
    else:
        k += 1
print("events", len(events), events[:5])
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": meta["baseline_start"], "end": meta["baseline_end"]},
    "target_analysed": {"start": tdays[0].isoformat(), "end": tdays[-1].isoformat()},
    "events": events,
    "complete": True,
    "caveats": "Region mean SST not checked against in-situ data.",
}
json.dump(report, open("output/report.json", "w"), indent=1)
print("wrote output/report.json")
