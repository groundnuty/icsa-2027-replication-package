import numpy as np, xarray, json, os, datetime as dt

os.makedirs("output", exist_ok=True)

# coordinates from the dataset (for exact dataset values)
ds = xarray.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
lat_all = ds.latitude.values; lon_all = ds.longitude.values
t_all = ds.time.values
lat = lat_all[(lat_all >= 54.13) & (lat_all <= 55.33)]
lon = lon_all[(lon_all >= 14.67) & (lon_all <= 15.87)]
tt = np.array([np.datetime64("2004-06-01") + np.timedelta64(k, "D") for k in range(92)])
t_idx = [int(np.where(t_all == v)[0][0]) for v in tt]
time = t_all[t_idx]
print("time first/last:", time[0], time[-1], "n:", len(time), "unique:", len(np.unique(time)))
assert len(lat) == 60 and len(lon) == 60

mask = np.load("/tmp/mask.npy")   # (3600, 92), row-major lat then lon
mask3 = mask.reshape(92, 60, 60)  # (time, lat, lon)
print("mask dtype/shape:", mask3.dtype, mask3.shape, "sum:", int(mask3.sum()))

da = xarray.DataArray(mask3, dims=("time", "latitude", "longitude"),
                      coords={"time": time, "latitude": lat, "longitude": lon},
                      name="mhw")
da.attrs = {"description": "1 where the grid cell is inside a per-cell marine heatwave (>=5 consecutive days with SST >= smoothed 90th-percentile climatology threshold, 1-2 day gaps joined) on that day, 0 otherwise; land cells 0. Region: 54.13-55.33N, 14.67-15.87E; period 2004-06-01 to 2004-08-31; baseline 1992-2002 (windows extended 1991-12-27..2003-01-05)."}
da.to_netcdf("output/mhw_mask.nc")
print("wrote output/mhw_mask.nc")

report = {
  "region": {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
  "events": [],
  "complete": True,
  "caveats": ("No regional MHW was detected: over 2004-06-01..2004-08-31 the maximum SST in the region "
              "(294.11 K, ~21.0 C) never exceeded the smoothed 90th-percentile threshold for >=5 consecutive "
              "days in any of the 3301 sea cells (of 3600 region cells; 299 land cells all-NaN). Only six isolated "
              "hot cell-days occurred (2004-08-01, 2004-08-04, 2004-08-05). Region cells are the 60x60 grid cells "
              "whose coordinates fall within the inclusive bounds (54.14..55.32 N, 14.68..15.86 E). Baseline pools "
              "for 1992-2002 used +-5 calendar-day windows, hence including 1991-12-27..1991-12-31 and "
              "2003-01-01..2003-01-05 as prescribed.")
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")
print(json.dumps(report, indent=2))
