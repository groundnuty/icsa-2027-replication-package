import numpy as np, datetime as dt, json, os
import xarray as xr

z = np.load("/work/cache_sst.npz"); tgt32 = z["tgt"]; tgt_ord = z["tgt_ord"]
zm = np.load("/work/cache_mhw.npz"); mhw = zm["mhw"]
dates = [dt.date.fromordinal(int(o)) for o in tgt_ord]
time_vals = np.array([np.datetime64(d, "ns") for d in dates])

# dataset coordinate values (float32 as stored in the dataset)
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20150601.nc", engine="h5netcdf")
lat_vals = ds["latitude"].isel(latitude=slice(132,192)).values  # float32
lon_vals = ds["longitude"].isel(longitude=slice(436,496)).values
ds.close()

assert mhw.dtype == np.uint8 and mhw.shape == (92, 60, 60)

ds_out = xr.Dataset(
    data_vars={"mhw": (("time", "lat", "lon"), mhw)},
    coords={
        "time": ("time", time_vals),
        "lat": ("lat", lat_vals),
        "lon": ("lon", lon_vals),
        # auxiliary copies carrying the dataset's coordinate names/values too
        "latitude": ("lat", lat_vals),
        "longitude": ("lon", lon_vals),
    },
)
os.makedirs("/work/output", exist_ok=True)
enc = {"mhw": {"dtype": "uint8", "_FillValue": None},
       "time": {"units": "days since 1950-01-01 00:00:00", "calendar": "standard"},
       "lat": {"_FillValue": None}, "lon": {"_FillValue": None},
       "latitude": {"_FillValue": None}, "longitude": {"_FillValue": None}}
ds_out.to_netcdf("/work/output/mhw_mask.nc", engine="h5netcdf", encoding=enc)
print("wrote /work/output/mhw_mask.nc", os.path.getsize("/work/output/mhw_mask.nc"), "bytes")

report = {
    "region": {"lat_min": 56.13, "lat_max": 57.33, "lon_min": 17.71, "lon_max": 18.91},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2015-06-01", "end": "2015-08-31"},
    "events": [{"onset": "2015-07-01", "end": "2015-07-08"}],
    "complete": True,
    "caveats": ("Per-cell MHW threshold/climatology pools are the specified baseline days 1992-01-01 to "
                "2002-12-31 plus the mandated +/-5 calendar-day extension days (1991-12-27 to 1991-12-31 "
                "and 2003-01-01 to 2003-01-05), which are not themselves baseline days. All 4020 required "
                "daily files were present; 3300 of 3600 region cells are sea cells (finite SST on every "
                "target day). All computations in float64 with hazen (type 5) percentiles."),
}
with open("/work/output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote /work/output/report.json")
print(json.dumps(report, indent=2))
