import numpy as np, json, os, time
T0 = time.time()

z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']
lat_vals, lon_vals = z['lat_vals'], z['lon_vals']
t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
tgt = zz['tgt'].astype(np.float64)
T, La, Lo = tgt.shape
C = La * Lo
doy_t = np.array([t_dates[k].astype(object).timetuple().tm_yday for k in range(T)], dtype=int)

sea_flat = np.isfinite(tgt).all(axis=0).reshape(-1)
nsea = int(sea_flat.sum())
print("sea cells:", nsea, "of", C)

hot = np.zeros((C, T), bool)
inmhw = np.zeros((C, T), bool)
def runs(b):
    d = np.diff(b.astype(np.int8))
    s_ = np.where(d == 1)[0] + 1
    e_ = np.where(d == -1)[0]
    return s_, e_

for c in range(C):
    if not sea_flat[c]:
        continue
    la, lo = divmod(c, Lo)
    h = tgt[:, la, lo] >= thr[c, doy_t]
    hot[c] = h
    inm = np.zeros(T, bool)
    s_, e_ = runs(np.concatenate(([False], h, [False])))
    for a, b in zip(s_, e_):
        if b - a >= 5:
            inm[a:b] = True
    gs, ge = runs(np.concatenate(([True], ~inm, [True])))
    for a, b in zip(gs, ge):
        if b - a in (1, 2) and a > 0 and inm[a - 1] and b < T and inm[b]:
            inm[a:b] = True
    inmhw[c] = inm

# self-check: verify gap-joining on a synthetic pattern
def cell_mhw(h, T):
    inm = np.zeros(T, bool)
    s_, e_ = runs(np.concatenate(([False], h, [False])))
    for a, b in zip(s_, e_):
        if b - a >= 5:
            inm[a:b] = True
    gs, ge = runs(np.concatenate(([True], ~inm, [True])))
    for a, b in zip(gs, ge):
        if b - a in (1, 2) and a > 0 and inm[a - 1] and b < T and inm[b]:
            inm[a:b] = True
    return inm
h1 = np.array([True]*5 + [False]*1 + [True]*5 + [False]*3 + [True]*6)   # join 1-gap, not 3-gap
print("test1:", cell_mhw(h1, len(h1)).astype(int).tolist())   # expect 11111111111000111111
h2 = np.array([True]*4 + [False]*2 + [True]*5)                 # 4-run is not MHW: no joining
print("test2:", cell_mhw(h2, len(h2)).astype(int).tolist())   # expect 0000000011111
h3 = np.array([True]*5 + [False]*2 + [True]*2 + [False]*1 + [True]*5)  # transitive join
print("test3:", cell_mhw(h3, len(h3)).astype(int).tolist())   # expect 11111111111111111

active = inmhw[sea_flat, :].any(axis=0) if nsea else np.zeros(T, bool)
s_, e_ = runs(np.concatenate(([False], active, [False])))
events = [{"onset": str(t_dates[a])[:10], "end": str(t_dates[b - 1])[:10]} for a, b in zip(s_, e_)]
print("active days:", int(active.sum()))
print("events:", json.dumps(events, indent=1))
print("hot cell-days:", int(hot.sum()), " in-MHW cell-days:", int(inmhw.sum()))
print("mean in-MHW fraction per sea cell:", round(inmhw[sea_flat].mean(), 4))

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
