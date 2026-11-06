import numpy as np, datetime as dt, pickle, json
import xarray as xr

mask = np.load("output/mask.npy")                      # (92, 3600) bool
tgt_days = pickle.load(open("output/tgt_days.pkl","rb"))
lat_full = np.load("output/lat.npy"); lon_full = np.load("output/lon.npy")
lat_idx = np.load("output/lat_idx.npy"); lon_idx = np.load("output/lon_idx.npy")
ev = pickle.load(open("output/events.pkl","rb"))

T = 92
mhw3 = mask.reshape(T, 60, 60).astype(np.uint8)
lat_c = lat_full[lat_idx].astype("float32")
lon_c = lon_full[lon_idx].astype("float32")
time_c = np.array([dt.date.fromisoformat(s) for s in tgt_days], dtype="datetime64[ns]")

ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw3,
             {"description": "1 = cell inside a per-cell MHW on that day, 0 = otherwise (land/non-sea cells are 0)"})},
    coords={"time": ("time", time_c, {"long_name": "Time", "standard_name": "time", "axis": "T"}),
            "lat": ("lat", lat_c, {"units": "degrees_north", "standard_name": "latitude"}),
            "lon": ("lon", lon_c, {"units": "degrees_east", "standard_name": "longitude"})},
    attrs={"title": "Marine heatwave mask, region 63.31-64.51N 21.31-22.51E, 2004-06-01..2004-08-31",
           "source": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (version 202506)",
           "method": "threshold = 90th pct (numpy method='hazen', HF type 5) of +-5-day windows per day-of-year over 1992-2002 baseline (day 60 = mean of days 59/61), 31-day centred circular smoothing; hot if SST(K) >= threshold; per-cell MHW >=5 consecutive hot days; gaps of 1-2 days joined; regional event = maximal run of days with >=1 cell in an MHW",
           "region": "lat 63.31..64.51, lon 21.31..22.51"}
)
ds.to_netcdf("output/mhw_mask.nc", encoding={
    "time": {"units": "seconds since 1981-01-01", "calendar": "proleptic_gregorian"}
})
print("netcdf written")

report = {
    "region": {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": [{"onset": s, "end": e} for s, e in ev],
    "complete": True,
    "caveats": "3299 of 3600 region grid cells are sea cells (finite SST on all target days); the 301 land cells are 0 in the mask. All needed baseline-window days (1991-12-27..2003-01-05) were present, so no pool values were missing. Method details: 90th percentile (numpy method='hazen', Hyndman-Fan type 5) of the +-5-day window pool per day-of-year over baseline 1992-2002, day-of-year 60 set to the mean of days 59 and 61, then 31-day unweighted centred moving mean with wrap-around over the 366-day year; a day is hot if SST (kelvin as stored) >= that day-of-year's smoothed threshold; per-cell MHW is a run of >=5 consecutive hot days with runs separated by 1-2 non-hot days joined (gap days included); regional events are maximal runs of days on which at least one sea cell is inside a per-cell MHW."
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("report written")
