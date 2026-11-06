import numpy as np, datetime, json
import xarray as xr

full_mask = np.load("/tmp/mhw/full_mask.npy")   # (92, 60, 60) uint8
lat = np.load("/tmp/mhw/lat.npy")
lon = np.load("/tmp/mhw/lon.npy")
events = np.load("/tmp/mhw/events.npy", allow_pickle=True)

d0 = datetime.date(2007, 6, 1)
ndays = full_mask.shape[0]
time_vals = np.array([np.datetime64((d0 + datetime.timedelta(days=i)).isoformat()) for i in range(ndays)])

ds = xr.Dataset(
    {"mhw": xr.DataArray(full_mask, dims=("time", "lat", "lon"),
                         coords={"time": time_vals, "lat": lat, "lon": lon})}
)
ds["mhw"].encoding = {"dtype": "uint8"}
ds["time"].encoding = {}
ds = ds.rename({"lat": "latitude", "lon": "longitude"})
# keep coordinate names as in the source dataset
ds.to_netcdf("output/mhw_mask.nc")

chk = xr.open_dataset("output/mhw_mask.nc")
print(chk)
print("mhw dtype:", chk["mhw"].dtype, "sum:", int(chk["mhw"].values.sum()))

report = {
    "region": {"lat_min": 59.93, "lat_max": 61.13, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2007-06-01", "end": "2007-08-31"},
    "events": [{"onset": str(e[0]), "end": str(e[1])} for e in events],
    "complete": True,
    "caveats": ("Thresholds/climatology per sea cell from baseline 1992-2002 with +/-5-day "
                "day-of-year windows (pools of 121 values incl. margin days 1991-12-27..1991-12-31 and "
                "2003-01-01..2003-01-05); 90th percentile via Hazen rule; 31-day circular smoothing; "
                "day-of-year 60 interpolated from 59 and 61. 3302 of 3600 region cells are sea cells "
                "(finite SST on all 92 target days). No NaNs in sea-cell baseline values.")
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
