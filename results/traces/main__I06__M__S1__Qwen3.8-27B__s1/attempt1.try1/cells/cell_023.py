import numpy as np, xarray as xr, datetime as dt, json, os

print("cwd:", os.getcwd())
base = "/data/icsa2027_data_20261101T090944Z/s1z"
ds = xr.open_dataset(f"{base}/sst_20120601.nc", engine="h5netcdf")
lat_all = ds.latitude.values
lon_all = ds.longitude.values
time_sample = ds.time.values
ds.close()
lat = lat_all[48:108]
lon = lon_all[353:413]
print("lat dtype", lat.dtype, "lon dtype", lon.dtype, "time dtype", time_sample.dtype)
print("lat first/last:", lat[0], lat[-1], "lon first/last:", lon[0], lon[-1])

mask = np.load("/tmp/mhw/mask.npy").astype(np.uint8)   # (92, 60, 60)
TG_START = dt.date(2012,6,1)
tgt_dates = [TG_START + dt.timedelta(days=i) for i in range(92)]
times = np.array([np.datetime64(dd.isoformat(), "ns") for dd in tgt_dates])

os.makedirs("output", exist_ok=True)
da = xr.DataArray(mask, dims=("time","lat","lon"),
                  coords={"time": times, "lat": lat, "lon": lon},
                  name="mhw")
da = da.astype("uint8")
da.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")
print("written output/mhw_mask.nc")

report = {
    "region": {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [
        {"onset": "2012-06-11", "end": "2012-06-16"},
        {"onset": "2012-07-25", "end": "2012-07-29"}
    ],
    "complete": True,
    "caveats": ("Region grid: 60x60=3600 cells (lat 54.46-55.64, lon 16.06-17.24 at 0.02 deg); "
                "3292 sea cells (SST finite on all 92 target days), 308 land cells set to 0. "
                "Per-cell thresholds/climatology from baseline 1992-2002 with +-5 calendar-day windows "
                "(pools include 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05); day 60 set to mean "
                "of days 59 and 61; wrap-around 31-day centred smoothing applied. 90th percentile computed "
                "with numpy nanquantile method='hazen' (Hyndman-Fan type 5). 25 per-cell MHWs found; no gap "
                "joining was triggered (all events were single runs of >=5 days).")
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("written output/report.json")
