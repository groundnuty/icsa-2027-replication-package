import numpy as np, datetime as dt, pickle, json
import xarray as xr
import h5py

mask = np.load("output/mask.npy")                      # (92, 3600) bool
tgt3 = np.load("output/tgt_sst.npy")
tgt_days = pickle.load(open("output/tgt_days.pkl","rb"))
lat_full = np.load("output/lat.npy"); lon_full = np.load("output/lon.npy")
lat_idx = np.load("output/lat_idx.npy"); lon_idx = np.load("output/lon_idx.npy")
ev = pickle.load(open("output/events.pkl","rb"))

# programmatic check of the example cell
c = 2074
idx = np.flatnonzero(mask[:, c])
print("cell 2074 mask days:", [tgt_days[i] for i in idx])
assert [tgt_days[i] for i in idx] == ["2004-08-08","2004-08-09","2004-08-10","2004-08-11","2004-08-12"]

# ---- get source time units for the output time coordinate
with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc","r") as f:
    tattrs = {k.decode() if isinstance(k, bytes) else k: (v.decode() if isinstance(v, bytes) else v)
              for k, v in f["time"].attrs.items()}
print("source time attrs:", tattrs)

# ---- build NetCDF
T = 92
mhw3 = mask.reshape(T, 60, 60).astype(np.uint8)
lat_c = lat_full[lat_idx].astype("float32")
lon_c = lon_full[lon_idx].astype("float32")
time_c = np.array([dt.date.fromisoformat(s) for s in tgt_days], dtype="datetime64[ns]")

ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw3, {"description": "1 = inside per-cell MHW, 0 = otherwise (land/non-sea cells are 0)"})},
    coords={"time": ("time", time_c, {k: v for k, v in tattrs.items() if k in ("units", "calendar", "standard_name", "long_name")}),
            "lat": ("lat", lat_c, {"units": "degrees_north", "standard_name": "latitude"}),
            "lon": ("lon", lon_c, {"units": "degrees_east", "standard_name": "longitude"})},
    attrs={"title": "Marine heatwave mask, region 63.31-64.51N 21.31-22.51E, 2004-06-01..2004-08-31",
           "source": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (version 202506)",
           "method": "90th pct (hazen/HF-type5) of +-5d windows over 1992-2002 baseline per day-of-year; 31-day circular smoothing; hot if SST>=thr; MHW >=5 consecutive hot days; gaps of 1-2 days joined",
           "region": "lat 63.31..64.51, lon 21.31..22.51"}
)
print(ds)
ds.to_netcdf("output/mhw_mask.nc")
print("netcdf written")

# ---- report
report = {
    "region": {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": [{"onset": s, "end": e} for s, e in ev],
    "complete": True,
    "caveats": "3299 of 3600 region grid cells are sea cells (finite SST on all target days); 301 land cells are set to 0. All pool days were available (windows 1991-12-27..2003-01-05 present). Threshold: 90th percentile (numpy method='hazen', Hyndman-Fan type 5) of +-5-day windows per day-of-year over 1992-2002, doy 60 set to mean of doys 59/61, then 31-day centred circular moving mean; hot day: SST(K) >= smoothed threshold."
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2))
