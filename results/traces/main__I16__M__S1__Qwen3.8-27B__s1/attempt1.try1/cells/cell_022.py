import numpy as np, json, xarray as xr, datetime as dt, os
from datetime import date

mhw = np.load("/tmp/mhw.npy")              # (92, 3600) bool
lat = np.load("/tmp/lat.npy"); lon = np.load("/tmp/lon.npy")
assert lat.shape==(60,) and lon.shape==(60,)

tdays = [date(2008,6,1)+dt.timedelta(i) for i in range(92)]
time_vals = np.array([d.isoformat()+"T00:00:00" for d in tdays], dtype="datetime64[ns]")

mask2d = mhw.reshape(92, 60, 60).astype(np.uint8)
ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mask2d, {"description":"1 = cell inside a per-cell MHW on that day (incl. gap days joined into the MHW); 0 otherwise (incl. land cells)"})},
    coords={"time": ("time", time_vals), "lat": ("lat", lat.astype(np.float32)), "lon": ("lon", lon.astype(np.float32))},
    attrs={"source":"cmems_obs-sst_bal_phy-temp_my_l4_P1D-m", "title":"Per-cell MHW mask, Baltic subregion, 2008-06-01..2008-08-31",
           "method":"Baltic MHW catalogue method: 90th pct (Hazen) thresholds + climatology from 1992-2002 pools (+/-5 d), day60=mean(59,61), 31-d centred wrap-around smoothing; per-cell MHW >=5 hot days, gaps <=2 d joined; regional events from union of cells"}
)
print(ds)
os.makedirs("output", exist_ok=True)
ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": 56.63, "lat_max": 57.83, "lon_min": 20.23, "lon_max": 21.43},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2008-06-01", "end": "2008-08-31"},
    "events": [{"onset": "2008-06-02", "end": "2008-06-10"}],
    "complete": True,
    "caveats": ("3304 of the 3600 region grid cells were sea cells (SST finite on every target day); 296 land cells are set to 0. "
                "Threshold/climatology pools used SST from 1991-12-27 to 2003-01-05 (baseline years 1992-2002 with the +/-5-day overhang); "
                "90th percentile computed as MATLAB quantile default / numpy method='hazen' (Hyndman-Fan type 5); day 60 = mean of days 59 and 61 "
                "before 31-day centred wrap-around smoothing. One regional MHW event detected (2008-06-02 to 2008-06-10).")
}
json.dump(report, open("output/report.json","w"), indent=2)
print(open("output/report.json").read())
