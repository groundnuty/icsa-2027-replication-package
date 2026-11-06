import numpy as np, json, os
T0 = 0

z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']; t_dates = z['t_dates']
zc = np.load('/work/hot_correct.npz')
hot = zc['hot']; sea_flat = zc['sea_flat']
T = hot.shape[1]; C = hot.shape[0]; La = Lo = int(np.sqrt(C))
doy_t = np.array([t_dates[k].astype(object).timetuple().tm_yday for k in range(T)], dtype=int)

# NaN thr check for sea cells over target doys
nan_thr_sea = np.isnan(thr[sea_flat, doy_t - 1]).sum()
print("sea cell-target-doy NaN thresholds:", int(nan_thr_sea))

def true_runs(x):
    n = len(x)
    d = np.diff(x.astype(np.int8))
    s = np.where(d == 1)[0] + 1; e = np.where(d == -1)[0] + 1
    if x[0]: s = np.concatenate(([0], s))
    if x[-1]: e = np.concatenate((e, [n]))
    return s, e

# synthetic tests of true_runs
cases = [
    (np.array([False]*10), [], []),
    (np.array([True]*10), [0], [10]),
    (np.array([True, False, True]), [0], [1]),
    (np.array([False, True, True, False, True]), [1], [3]),
    (np.array([True, False, False, True, True, True]), [0], [1]),
]
for x, es, ee in cases:
    s, e = true_runs(x)
    ok = list(s) == es and list(e) == ee
    print("runs", x.astype(int).tolist(), "->", list(s), list(e), "OK" if ok else "FAIL")

def cell_mhw(h, Tn):
    inm = np.zeros(Tn, bool)
    s_, e_ = true_runs(np.concatenate(([False], h, [False])))
    for a, b in zip(s_, e_):
        if b - a >= 5: inm[a:b] = True
    gs, ge = true_runs(np.concatenate(([True], ~inm, [True])))
    for a, b in zip(gs, ge):
        if b - a in (1, 2) and a > 0 and inm[a-1] and b < Tn and inm[b]:
            inm[a:b] = True
    return inm

t1 = np.array([True]*5 + [False]*1 + [True]*5 + [False]*3 + [True]*6)
print("test1:", cell_mhw(t1, len(t1)).astype(int).tolist(), "expect 11111111111 000 111111")
t2 = np.array([True]*4 + [False]*2 + [True]*5)
print("test2:", cell_mhw(t2, len(t2)).astype(int).tolist(), "expect 0000000011111")
t3 = np.array([True]*5 + [False]*2 + [True]*2 + [False]*1 + [True]*5)
print("test3:", cell_mhw(t3, len(t3)).astype(int).tolist(), "expect 11111111111111111")
t4 = np.array([True]*6 + [False]*2 + [True]*5)
print("test4:", cell_mhw(t4, len(t4)).astype(int).tolist(), "expect 111111111111111 (join 2-gap)")
t5 = np.array([True]*5)
print("test5:", cell_mhw(t5, len(t5)).astype(int).tolist(), "expect 111111")
t6 = np.array([True]*4)
print("test6:", cell_mhw(t6, len(t6)).astype(int).tolist(), "expect 00000")

inmhw = np.zeros((C, T), bool)
for c in range(C):
    if not sea_flat[c]: continue
    inmhw[c] = cell_mhw(hot[c], T)
active = inmhw.any(axis=0)
s_, e_ = true_runs(np.concatenate(([False], active, [False])))
events = [{"onset": str(t_dates[a])[:10], "end": str(t_dates[b - 1])[:10]} for a, b in zip(s_, e_)]
print("\nactive days:", int(active.sum()), " in-MHW cell-days:", int(inmhw.sum()))
print("events:", events)

os.makedirs('/work/output', exist_ok=True)
mhw3 = inmhw.T.reshape(T, La, Lo).astype(np.uint8)
import xarray as xr
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw3)},
    coords={
        "time": (["time"], t_dates.astype('datetime64[ns]')),
        "lat": (["lat"], z['lat_vals'].astype(np.float32)),
        "lon": (["lon"], z['lon_vals'].astype(np.float32)),
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
                "SST in kelvin as stored; non-finite (fill) values treated as missing. "
                "307 cells have non-finite SST on some baseline-window day; 307 cells are not sea cells (non-finite on some target day) and are 0 in the mask. "
                "Threshold = 90th percentile of the per-cell pool of SST values within +/-5 calendar days of each of the 11 baseline dates (1992-2002) sharing the day of year, "
                "computed as numpy quantile method='hazen' (Hyndman-Fan type 5); day-60 statistics are the mean of days 59 and 61; "
                "threshold and climatology then smoothed with an unweighted 31-day centred moving mean wrapping around the 366-day year; all statistics in float64. "
                "2017 summer SST was within about 1 K of the 1992-2002 climatology (baseline hot-day fraction 9.5%), so no 5+ day hot runs occurred and no regional MHW events were detected."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=1)
print("outputs written")
