import numpy as np, pickle, json, os
from datetime import date, timedelta
import xarray as xr

meta = pickle.load(open("/tmp/target.pkl","rb"))
T = meta["T"]; sea = meta["sea"]
lat32 = meta["lat"]; lon32 = meta["lon"]
slat, slon = meta["slat"], meta["slon"]
tc = pickle.load(open("/tmp/thrclim.pkl","rb"))
thr_s = tc["thr_s"]

leap_cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return leap_cum[d.month-1] + d.day
d0 = date(2017,6,1); dates=[]; cur=d0
while cur <= date(2017,8,31): dates.append(cur); cur += timedelta(days=1)
assert len(dates) == 92
doys = np.array([doy(d) for d in dates]) - 1

def cell_mhw(h):
    m = np.zeros_like(h, bool)
    if not h.any():
        return m
    idx = np.flatnonzero(h)
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[breaks+1]])
    ends   = np.concatenate([idx[breaks], [idx[-1]]])
    runs = [(s,e) for s,e in zip(starts, ends) if e-s+1 >= 5]
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    for s,e in merged:
        m[s:e+1] = True
    return m

Tf = T.reshape(92, 3600)
sea_flat = sea.reshape(3600)
hot = Tf >= thr_s[doys]                       # NaN SST -> False
M = np.zeros((92, 3600), dtype=np.uint8)
n_mhw_cells = 0
for c in np.flatnonzero(sea_flat):
    if hot[:, c].any():
        m = cell_mhw(hot[:, c])
        M[:, c] = m.astype(np.uint8)
        if m.any():
            n_mhw_cells += 1
M3 = M.reshape(92, 60, 60)
active = M.reshape(92, 3600)[:, sea_flat].any(axis=1)
events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]: j += 1
        events.append({"onset": dates[i].isoformat(), "end": dates[j].isoformat()})
        i = j+1
    else:
        i += 1
print("hot days (any sea cell):", int(hot[:, sea_flat].any(axis=1).sum()))
print("sea cells with >=1 MHW:", n_mhw_cells)
print("mhw mask sum:", int(M.sum()))
print("events:", events)

os.makedirs("output", exist_ok=True)
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), M3.astype("uint8"))},
    coords={
        "time": ("time", np.array([d.isoformat() for d in dates], dtype="datetime64[ns]")),
        "lat": ("lat", lat32[slat].astype("float32")),
        "lon": ("lon", lon32[slon].astype("float32")),
    },
)
ds_out.to_netcdf("output/mhw_mask.nc")
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2017-06-01", "end": "2017-08-31"},
    "events": events,
    "complete": True,
    "caveats": "",
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")
print(json.dumps(report))
