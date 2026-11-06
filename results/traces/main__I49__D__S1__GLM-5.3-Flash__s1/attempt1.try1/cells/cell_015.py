import numpy as np, xarray as xr, datetime as dt, json, os

mhw = np.load('/work/mhw.npy') if os.path.exists('/work/mhw.npy') else None
if mhw is None:
    # recompute quickly from saved cube_t + thresh_s
    cube_t = np.load('/work/cube_t.npy'); thresh_s = np.load('/work/thresh_s.npy')
    dates_t = [dt.date.fromisoformat(l.strip()) for l in open('/work/dates_t.txt') if l.strip()]
    doy_md = lambda d: dt.date(2000, d.month, d.day).timetuple().tm_yday
    hot = cube_t >= thresh_s[np.array([doy_md(d) for d in dates_t]) - 1]
    def per_cell_mhw_mask(h):
        idx = np.flatnonzero(h)
        if idx.size == 0: return np.zeros_like(h)
        br = np.flatnonzero(np.diff(idx) > 1)
        st = np.r_[0, br+1]; en = np.r_[br, idx.size-1]
        ev = []
        for s, e in zip(st, en):
            if idx[e]-idx[s]+1 < 5: continue
            rs, re = idx[s], idx[e]
            if ev and rs - ev[-1][1] - 1 <= 2: ev[-1] = (ev[-1][0], re)
            else: ev.append((rs, re))
        m = np.zeros_like(h)
        for s, e in ev: m[s:e+1] = True
        return m
    mhw = np.zeros_like(hot)
    for i in range(hot.shape[1]):
        for j in range(hot.shape[2]):
            mhw[:, i, j] = per_cell_mhw_mask(hot[:, i, j])
np.save('/work/mhw.npy', mhw)

lat_out = np.load('/work/lat_out.npy'); lon_out = np.load('/work/lon_out.npy')
dates_t = [dt.date.fromisoformat(l.strip()) for l in open('/work/dates_t.txt') if l.strip()]
time_vals = np.array([np.datetime64(f"{d.isoformat()}T00:00:00.000000000") for d in dates_t])

os.makedirs('/work/output', exist_ok=True)
ds = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw.astype(np.uint8))},
    coords={"time": time_vals, "lat": lat_out, "lon": lon_out},
    attrs={
        "title": "Per-cell marine heatwave mask, Baltic Sea region, 2019-06-01 to 2019-08-31",
        "method": "hot day = analysed_sst >= cell's 90th-percentile threshold (1992-2002 baseline, hazen/quantile type 5, +-5-day calendar windows, day-60 filled from days 59/61, 31-day circular moving mean); per-cell MHW = run >= 5 hot days, gaps <= 2 non-hot days joined; land/ice cells = 0",
        "source_dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
    },
)
enc = {"mhw": {"dtype": "uint8", "_FillValue": None},
       "lat": {"_FillValue": None}, "lon": {"_FillValue": None}, "time": {"_FillValue": None}}
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf', encoding=enc)

events = [
    {"onset": "2019-06-05", "end": "2019-06-22"},
    {"onset": "2019-07-19", "end": "2019-07-29"},
    {"onset": "2019-08-26", "end": "2019-08-31"},
]
report = {
    "region": {"lat_min": 64.51, "lat_max": 65.71, "lon_min": 21.97, "lon_max": 23.17},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("Baseline pools are built from the 1992-2002 baseline years plus the +-5-calendar-day "
                "extension days specified by the method (1991-12-27 to 1991-12-31 and 2003-01-01 to "
                "2003-01-05), so the first/last days actually used are 1991-12-27 and 2003-01-05; all "
                "4118 days in that span were present in the dataset. Day of year 60 (29 Feb) has no pool "
                "of its own and was set to the mean of days 59 and 61 before smoothing; smoothing is an "
                "unweighted 31-day centred moving mean wrapping modulo 366. Sea cells are the 3286 region "
                "cells with finite SST on every target day; the other 314 cells (land/ice) are 0 in the "
                "mask and excluded. Regional events run from the first to the last day on which at least "
                "one sea cell is inside a per-cell MHW: 2019-06-05 to 2019-06-22 (18 d), 2019-07-19 to "
                "2019-07-29 (11 d), 2019-08-26 to 2019-08-31 (6 d, cut off by the end of the target "
                "period). All computations were done in float64."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("written:", os.listdir('/work/output'))

# verify outputs
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(chk)
m = chk.mhw.values
print("dtype:", m.dtype, "| shape:", m.shape, "| ones:", int(m.sum()), "| zeros:", int((m==0).sum()))
print("time:", chk.time.values[0], "->", chk.time.values[-1])
print("lat:", chk.lat.values[0], chk.lat.values[-1], "| lon:", chk.lon.values[0], chk.lon.values[-1])
print("report:", json.dumps(json.load(open('/work/output/report.json')), indent=2)[:1200])
