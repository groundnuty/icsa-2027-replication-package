import numpy as np, json, os, time
from datetime import date
T0 = time.time()

z = np.load('/work/stats.npz', allow_pickle=False)
thr, clim = z['thr'], z['clim']
lat_vals, lon_vals = z['lat_vals'], z['lon_vals']
t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
tgt = zz['tgt'].astype(np.float64)          # (92, 60, 60)
T, La, Lo = tgt.shape
C = La * Lo
doy_t = np.array([t_dates[k].astype(object).timetuple().tm_yday for k in range(T)], dtype=int)

sea = np.isfinite(tgt).all(axis=0)
nsea = int(sea.sum())
sea_flat = sea.reshape(-1)
print("sea cells:", nsea, "of", C)

hot = np.zeros((C, T), bool)
inmhw = np.zeros((C, T), bool)
for c in range(C):
    if not sea_flat[c]:
        continue
    la, lo = divmod(c, Lo)
    s = tgt[:, la, lo]
    h = s >= thr[c, doy_t]
    hot[c] = h
    inm = np.zeros(T, bool)
    d = np.diff(np.concatenate(([False], h, [False])))
    starts = np.where(d == 1)[0] + 1
    ends = np.where(d == -1)[0]
    keep = (ends - starts) >= 5
    for s_, e_ in zip(starts[keep], ends[keep]):
        inm[s_:e_] = True
    d2 = np.diff(np.concatenate(([True], ~inm, [True])))
    gs = np.where(d2 == 1)[0] + 1
    ge = np.where(d2 == -1)[0]
    for g_, ge_ in zip(gs, ge):
        if ge_ - g_ in (1, 2) and g_ > 0 and inm[g_ - 1] and ge_ < T and inm[ge_]:
            inm[g_:ge_] = True
    inmhw[c] = inm

active = inmhw[sea_flat, :].any(axis=0) if nsea else np.zeros(T, bool)
d3 = np.diff(np.concatenate(([False], active, [False])))
ev_s = np.where(d3 == 1)[0] + 1
ev_e = np.where(d3 == -1)[0]
events = [{"onset": str(t_dates[s])[:10], "end": str(t_dates[e - 1])[:10]} for s, e in zip(ev_s, ev_e)]
print("events:", json.dumps(events, indent=1))
print("hot cell-days:", int(hot.sum()), " in-MHW cell-days:", int(inmhw.sum()))
act_days = int(active.sum())
print("active days:", act_days, "first:", str(t_dates[0]), "last:", str(t_dates[-1]))

os.makedirs('/work/output', exist_ok=True)
mhw3 = inmhw.T.reshape(T, La, Lo).astype(np.uint8)
import xarray as xr
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw3)},
    coords={
        "time": (["time"], t_dates.astype('datetime64[ns]')),
        "lat": (["lat"], lat_vals.astype(np.float32)),
        "lon": (["lon"], lon_vals.astype(np.float32)),
    },
)
ds_out.to_netcdf('/work/output/mhw_mask.nc')

report = {
    "region": {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2017-06-01", "end": "2017-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("Region bounds snap to the 0.02-deg grid: cells analysed span 58.70-59.88 N, 18.70-19.88 E (60x60=3600 cells). "
                "SST in kelvin; non-finite (fill) values treated as missing. 307 cells have non-finite SST on some baseline window day. "
                "307 cells are not sea cells (non-finite on some target day) and are 0 in the mask. "
                "90th percentile computed as numpy quantile method='hazen' (Hyndman-Fan type 5); day-60 statistics are the mean of days 59 and 61; "
                "threshold and climatology smoothed with a 31-day centred wrap-around moving mean (float64)."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=1)
print("outputs written, elapsed:", round(time.time()-T0, 1))
