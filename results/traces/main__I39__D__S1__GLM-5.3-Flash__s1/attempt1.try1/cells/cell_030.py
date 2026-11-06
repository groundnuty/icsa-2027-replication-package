import numpy as np, json, xarray as xr, datetime as dt

coords = np.load('/work/coords.npz', allow_pickle=True)
time_tgt = coords['time_tgt']
lat = coords['lat']; lon = coords['lon']
mhw = np.load('/work/mhw.npy')   # (92,60,60) uint8
sea = np.load('/work/sea.npy')

# regional events recomputed for the report
mhw_sea = mhw * sea[None].astype(np.uint8)
active = mhw_sea.reshape(mhw_sea.shape[0], -1).max(axis=1).astype(bool)
events = []
j = 0; n = len(active)
while j < n:
    if active[j]:
        e = j
        while e+1 < n and active[e+1]: e += 1
        events.append((j, e)); j = e + 1
    else:
        j += 1
events_list = [{"onset": str(np.datetime64(time_tgt[s], 'D')),
                "end":   str(np.datetime64(time_tgt[e], 'D'))} for s, e in events]

# --- mhw_mask.nc : dims (time, lat, lon), variable mhw uint8, dataset coordinate values ---
time_dt = time_tgt.astype('datetime64[ns]')
ds_out = xr.Dataset(
    data_vars={"mhw": (("time", "lat", "lon"), mhw.astype(np.uint8))},
    coords={
        "time": ("time", time_dt),
        "lat": ("lat", lat.astype(np.float32)),
        "lon": ("lon", lon.astype(np.float32)),
    },
)
ds_out["mhw"].attrs = {"long_name": "per-cell marine heatwave mask (1 = inside MHW)", "units": "1"}
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print('wrote mhw_mask.nc')

# --- report.json ---
report = {
    "region": {"lat_min": 60.49, "lat_max": 61.69, "lon_min": 17.25, "lon_max": 18.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": events_list,
    "complete": True,
    "caveats": ("Data source: the given directory icsa2027_data_20261101T090944Z/s1z held only a small "
                "daily sample (1982-01-01..1984-09-26) of the product; the full dataset for "
                "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP, 1982-01-01..2023-12-31, "
                "same variable analysed_sst, grid and attributes) was found as the single file "
                "s2z/sst_s2.nc in the sibling directory and was used. Baseline years 1992-2002 with "
                "day-of-year pools of +/-5 calendar days (windows reach 1991-12-27..1991-12-31 and "
                "2003-01-01..2003-01-05, as prescribed); day 60 (29 Feb) filled from days 59/61 then "
                "both climatologies smoothed with a centred, wrap-around 31-day moving mean. "
                "Sea cells = 3293 cells with finite SST on every target day (of 3600 in the region; "
                "307 land cells are all-NaN and masked 0). Per-cell MHW: hot if SST >= 90th-percentile "
                "threshold (Hazen/type 5, NaN-ignoring), runs >= 5 days, gaps of 1-2 days joined; "
                "found over 2010-06-01..2010-08-31 only. One regional event: 2010-06-28..2010-07-23 "
                "(26 active days). All quantities computed in float64; threshold/climatology and MHW "
                "logic verified against independent pure-Python recomputation (agreement to ~2e-13).")
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print('wrote report.json')
print(json.dumps({k: (v if k != 'caveats' else v[:80] + '...') for k, v in report.items()}, indent=2))
