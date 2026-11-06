import numpy as np, json
from datetime import date, timedelta
import xarray as xr

z = np.load("/tmp/sst_data.npz")
T = z["T"]; ttimes = z["ttimes"]
s2 = np.load("/tmp/step2.npz")
thr_s = s2["thr_s"]; sea = s2["sea"]; lat, lon = s2["lat"], s2["lon"]

cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return cum[d.month-1] + d.day
def to_date(ts):
    s = str(ts); return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
tgt_dates = [to_date(t) for t in ttimes]
tgt_doy = np.array([doy(d) for d in tgt_dates]) - 1

T60 = T.reshape(len(tgt_dates), 60*60)
sea_flat = sea.ravel()
ncell = int(sea.sum())

Ts = T60[:, sea_flat]                 # (92, ncell)
th = thr_s[:, tgt_doy].T              # (92, ncell)
hot = Ts >= th
print("hot fraction:", hot.mean())

def mhw_mask(h):
    n = len(h)
    out = np.zeros(n, dtype=bool)
    idx = np.where(h)[0]
    if idx.size == 0:
        return out
    brk = np.where(np.diff(idx) > 1)[0] + 1
    runs = list(np.split(idx, brk))
    evs = []
    last_i = -1
    for i, r in enumerate(runs):
        if len(r) >= 5:
            if evs and i == last_i + 1 and (r[0] - (runs[last_i][-1] + 1)) <= 2:
                evs[-1] = (evs[-1][0], r[-1])
            else:
                evs.append((r[0], r[-1]))
            last_i = i
    for s_, e_ in evs:
        out[s_:e_+1] = True
    return out

inmhw = np.array([mhw_mask(hot[:, c]) for c in range(ncell)])
print("in-MHW cell-day fraction:", inmhw.mean())

active = inmhw.any(axis=1)
print("active days:", int(active.sum()), "of", len(active))
act_idx = np.where(active)[0]
if act_idx.size:
    abrk = np.where(np.diff(act_idx) > 1)[0] + 1
    aruns = list(np.split(act_idx, abrk))
    events = [(tgt_dates[r[0]], tgt_dates[r[-1]]) for r in aruns]
else:
    events = []
print("regional events:", len(events))
for o, e in events:
    print("  ", o, "->", e, f"({(e-o).days+1} d)")

mask = np.zeros((T.shape[0], 60, 60), dtype=np.uint8)
mask[:, sea] = inmhw.T.astype(np.uint8)

ds = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mask)},
    coords={"time": ("time", np.asarray(ttimes, dtype="datetime64[ns]")),
            "lat": ("lat", lat.astype(np.float32)),
            "lon": ("lon", lon.astype(np.float32))})
ds.to_netcdf("output/mhw_mask.nc")
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": o.isoformat(), "end": e.isoformat()} for o, e in events],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
