import numpy as np, json, datetime as dt, os
import xarray as xr

OUT="/tmp/mhw"
sea = np.load(f"{OUT}/sea.npy")
D_tgt = np.load(f"{OUT}/D_tgt.npy")
dates = json.load(open(f"{OUT}/dates.json"))
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]
tgt = np.load(f"{OUT}/tgt.npy").reshape(92, 3600)
thr_s = np.load(f"{OUT}/thr_s.npy")

hot = (tgt >= thr_s[D_tgt]) & sea[None,:]

def runs_of(h):
    pad = np.concatenate([[False], np.asarray(h), [False]])
    d = np.diff(pad.astype(np.int8))
    return list(zip(np.flatnonzero(d==1).tolist(), (np.flatnonzero(d==-1)-1).tolist()))

def cell_events(h):
    kept = [(s,e) for s,e in runs_of(h) if e-s+1 >= 5]
    merged = []
    for s,e in kept:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    return merged

mhw = np.zeros((92, 3600), dtype=np.uint8)
for c in np.flatnonzero(sea):
    for s,e in cell_events(hot[:,c]):
        mhw[s:e+1, c] = 1

active = mhw.sum(axis=1) > 0
ev = runs_of(active)
events = [{"onset": tgt_dates[s].isoformat(), "end": tgt_dates[e].isoformat()} for s,e in ev]
print("per-cell MHWs total:", int(sum(len(cell_events(hot[:,c])) for c in np.flatnonzero(sea))))
print("events:", events)

os.makedirs("output", exist_ok=True)
lat = np.load(f"{OUT}/lat_f32.npy"); lon = np.load(f"{OUT}/lon_f32.npy")
time_vals = np.array([dt.datetime(d.year,d.month,d.day) for d in tgt_dates], dtype="datetime64[ns]")
mhw3 = mhw.reshape(92, 60, 60)
ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw3, {"description": "1 where the cell is inside a per-cell MHW on that day, 0 otherwise (land cells 0)"})},
    coords={"time": ("time", time_vals), "lat": ("lat", lat), "lon": ("lon", lon)},
)
ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.41, "lat_max": 58.61, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2013-06-01", "end": "2013-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("3309 of 3600 region cells were sea cells (finite SST on all 92 target days); land cells are 0 in the mask. "
                "Per-cell MHW = run of >=5 consecutive hot days (SST >= smoothed doy threshold, 90th pct, hazen, 121-value pool), "
                "then MHWs separated by 1-2 non-hot days joined; no cell met the 5-day duration, so there are no regional events. "
                "The 2013 summer was warm vs the 1992-2002 climatology (up to ~+2.7 K) but exceeded the 90th-percentile threshold only on "
                "isolated days (max per-cell hot run length 4). baseline_analysed spans all days whose SST values were used, i.e. the "
                "1992-2002 baseline plus the +-5-day window extensions 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. "
                "Thresholds/climatology computed in float64; day 60 set to mean of days 59/61 then 31-day circular moving mean."),
}
with open("output/report.json","w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
