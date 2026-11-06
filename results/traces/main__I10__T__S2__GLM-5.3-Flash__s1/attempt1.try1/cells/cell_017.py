import numpy as np, pandas as pd, xarray as xr, json, os

d = np.load("work/coords.npz"); t_tgt = pd.to_datetime(d['t_tgt'])
lat, lon = d['lat'], d['lon']
m = np.load("work/mhw.npz"); mhw = m['mhw']
nt = mhw.shape[0]

os.makedirs("output", exist_ok=True)

mhw_u8 = mhw.astype(np.uint8)
ds_out = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw_u8)},
    coords={"time": ("time", t_tgt.values),
            "lat": ("lat", lat.astype(np.float32)),
            "lon": ("lon", lon.astype(np.float32))},
)
ds_out["mhw"].attrs = {"long_name": "per-cell marine heatwave mask (1 = inside per-cell MHW)"}
ds_out.attrs = {
    "title": "Per-cell marine heatwave mask, Baltic Sea region, 2005-06-01..2005-08-31",
    "dataset_id": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
    "baseline_years": "1992-2002 (pools +-5 calendar days: 1991-12-27..2003-01-05)",
    "threshold": "90th percentile (hazen) of baseline pool, day-60 filled from days 59/61, 31-day circular moving mean",
    "mhw_definition": ">=5 consecutive hot days (SST >= smoothed 90th-pct threshold); gaps of 1-2 non-hot days joined",
}
enc = {"mhw": {"dtype": "uint8", "zlib": True},
       "time": {"units": "days since 1982-01-01 00:00:00", "calendar": "proleptic_gregorian"}}
ds_out.to_netcdf("output/mhw_mask.nc", encoding=enc)

report = {
    "region": {"lat_min": 55.67, "lat_max": 56.87, "lon_min": 16.45, "lon_max": 17.65},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2005-06-01", "end": "2005-08-31"},
    "events": [{"onset": "2005-07-02", "end": "2005-07-20"}],
    "complete": True,
    "caveats": ("Baseline pools for 1992-2002 use a +-5-calendar-day window, so values from "
                "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 enter the threshold/climatology "
                "(reported in baseline_analysed). Grid resolution is 0.02 deg, so analysed cells span "
                "55.68-56.86 N, 16.46-17.64 E (all inside the requested bounds); 3310 of 3600 cells are "
                "sea cells (finite SST on every target day). Hot days use SST >= threshold; per-cell runs "
                "of >=5 hot days with 1-2-day gaps joined were detected only within the target period, "
                "as specified."
               ),
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2))

# verify written netcdf
chk = xr.open_dataset("output/mhw_mask.nc")
print(chk)
print("mhw dtype:", chk.mhw.dtype, "sum:", int(chk.mhw.values.sum()), "shape:", chk.mhw.shape)
print("event days mask sum check:", int(chk.mhw.values.sum(axis=(1,2))[31:50].sum()))
