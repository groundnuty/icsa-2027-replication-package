import numpy as np, json, datetime as dt, os

OUT="/tmp/mhw"
tgt = np.load(f"{OUT}/tgt.npy").reshape(92, 3600)
thr_s = np.load(f"{OUT}/thr_s.npy")
sea = np.load(f"{OUT}/sea.npy")
D_tgt = np.load(f"{OUT}/D_tgt.npy")
dates = json.load(open(f"{OUT}/dates.json"))
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]

hot = tgt >= thr_s[D_tgt]            # (92, 3600); NaN thr -> False
hot = hot & sea[None, :]
print("hot days total:", int(hot.sum()))

def runs_of(h):
    # maximal True runs in bool array -> list of (start,end) inclusive
    h = np.asarray(h)
    pad = np.concatenate([[False], h, [False]])
    d = np.diff(pad.astype(np.int8))
    s = np.flatnonzero(d == 1)
    e = np.flatnonzero(d == -1) - 1
    return list(zip(s.tolist(), e.tolist()))

def cell_mhw_days(h):
    runs = runs_of(h)
    kept = [(s,e) for s,e in runs if e - s + 1 >= 5]
    merged = []
    for s,e in kept:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    out = np.zeros(len(h), dtype=bool)
    for s,e in merged:
        out[s:e+1] = True
    return out, len(kept), len(merged)

mhw = np.zeros((92, 3600), dtype=np.uint8)
n5 = 0; nmerged = 0
sea_idx = np.flatnonzero(sea)
for c in sea_idx:
    days, k5, km = cell_mhw_days(hot[:, c])
    mhw[:, c] = days
    n5 += k5; nmerged += km
print("cells:", len(sea_idx), "raw >=5 runs:", n5, "after joining:", nmerged)

active = mhw.sum(axis=1) > 0
ev_runs = runs_of(active)
events = [(tgt_dates[s].isoformat(), tgt_dates[e].isoformat()) for s,e in ev_runs]
print("active days:", int(active.sum()), "of 92")
print("events:", events)

# day-by-day activity for inspection
print("active first/last:", (tgt_dates[0].isoformat() if active[0] else None),
      (tgt_dates[-1].isoformat() if active[-1] else None))

# ---- write outputs ----
os.makedirs("/output", exist_ok=True)
import xarray as xr
lat = np.load(f"{OUT}/lat_f32.npy"); lon = np.load(f"{OUT}/lon_f32.npy")
time_vals = np.array([dt.datetime(d.year, d.month, d.day) for d in tgt_dates], dtype="datetime64[ns]")

mhw3 = mhw[:, :, :]  # already (time, lat, lon)
ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw3, {"description": "1 if cell is inside a per-cell MHW on that day, 0 otherwise (land=0)"})},
    coords={"time": ("time", time_vals), "lat": ("lat", lat), "lon": ("lon", lon)},
)
ds.to_netcdf("/output/mhw_mask.nc")
print("wrote /output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.41, "lat_max": 58.61, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2013-06-01", "end": "2013-08-31"},
    "events": [{"onset": s, "end": e} for s,e in events],
    "complete": True,
    "caveats": ("Sea cells = region cells finite on all 92 target days (3309 of 3600). "
                "Threshold/climatology pools used baseline 1992-2002 values plus the +-5-day "
                "window extension days 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05, per the method. "
                "All pool sizes were 121; doy 60 set to mean of doy 59/61 then 31-day circular smoothing applied."),
}
with open("/output/report.json","w") as f:
    json.dump(report, f, indent=2)
print("wrote /output/report.json")
print(json.dumps(report, indent=2))
