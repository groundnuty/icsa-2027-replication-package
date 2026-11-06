import numpy as np, datetime as dt, os, json
import xarray as xr

OUT = "/work/mhw"
os.makedirs("output", exist_ok=True)

z1 = np.load(f"{OUT}/results1.npz")
z2 = np.load(f"{OUT}/results2.npz")
co = np.load(f"{OUT}/coords.npz")
sea_r = z1["sea_r"].astype(int); sea_c = z1["sea_c"].astype(int)
mcell = z2["mcell"]  # (92, nsea)

# full region mask
mfull = np.zeros((92, 60, 60), dtype=np.uint8)
mfull[:, sea_r, sea_c] = mcell
print("mfull: nonzero days:", int((mfull.sum(axis=(1,2))>0).sum()),
      "total 1s:", int(mfull.sum()), "max per day:", int(mfull.sum(axis=(1,2)).max()))

# time coordinate: dataset values (seconds since 1981-01-01)
epoch = dt.date(1981,1,1)
time_vals = np.array([(dt.date(2004,6,1) + dt.timedelta(days=k) - epoch).total_seconds() for k in range(92)], dtype=np.float64)

ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mfull)},
    coords={
        "time": ("time", time_vals, {"units":"seconds since 1981-01-01","calendar":"proleptic_gregorian","standard_name":"time","axis":"T"}),
        "lat":  ("lat",  co["lat"], {"units":"degrees_north","standard_name":"latitude","axis":"Y"}),
        "lon":  ("lon",  co["lon"], {"units":"degrees_east","standard_name":"longitude","axis":"X"}),
    },
)
ds["mhw"].attrs = {"long_name":"marine heatwave mask","description":"1 where grid cell is inside a per-cell MHW on that day (gap days of merged MHWs included), 0 otherwise (land cells 0)"}
ds.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")
print("wrote output/mhw_mask.nc")

# verify round-trip
chk = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(chk)
assert chk["mhw"].dtype == np.uint8
assert tuple(chk["mhw"].shape) == (92, 60, 60)
assert int(chk["mhw"].values.sum()) == int(mfull.sum())
np.testing.assert_array_equal(chk["lat"].values, co["lat"])
np.testing.assert_array_equal(chk["lon"].values, co["lon"])
print("mhw_mask.nc verified")

report = {
    "region": {"lat_min": 57.57, "lat_max": 58.77, "lon_min": 10.25, "lon_max": 11.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": [{"onset": "2004-08-05", "end": "2004-08-15"}],
    "complete": True,
    "caveats": ("Baltic MHW detection per published catalogue method: baseline years 1992-2002; the per-day-of-year pool uses all SST values within +/-5 calendar days of each baseline date, "
                "so data from 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 were also used (hence baseline_analysed span). Thresholds are the 90th percentile of the pool using MATLAB-default "
                "quantile (numpy method='hazen', Hyndman-Fan type 5), ignoring NaN; day 60 (29 Feb) set to the mean of days 59 and 61; both threshold and climatology then smoothed with a wrapping "
                "31-day centred moving mean. 296 of 3600 regional grid cells had non-finite SST on at least one target day and were treated as land (mhw=0); 3304 sea cells were analysed. "
                "Per-cell MHWs are runs of >=5 consecutive days with SST >= threshold, merged when separated by 1-2 non-hot days (gap days included). One regional event detected: 2004-08-05 to 2004-08-15.")
}
with open("output/report.json","w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2)[:600])
print("wrote output/report.json")
