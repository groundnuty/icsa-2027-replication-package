import numpy as np, os, json, xarray as xr
print("cwd:", os.getcwd())
mask = np.load("/tmp/mask_lit.npy").astype(np.uint8)  # (92, 60, 60)
import pickle
with open("/tmp/data.pkl","rb") as f: D = pickle.load(f)
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
lat = ds.latitude.values[278:338].astype(np.float32)
lon = ds.longitude.values[613:673].astype(np.float32)
time = ds.time.values[151:243]
print("coords:", time[0], time[-1], lat[0], lat[-1], lon[0], lon[-1], "mask shape", mask.shape)

out = xr.Dataset(
    {"mhw": (("time","lat","lon"), mask)},
    coords={"time": time, "lat": lat, "lon": lon},
)
outdir = os.path.join(os.getcwd(), "output")
os.makedirs(outdir, exist_ok=True)
out["mhw"].attrs["long_name"] = "marine heatwave (per-cell) mask, 1 = inside MHW"
nc_path = os.path.join(outdir, "mhw_mask.nc")
out.to_netcdf(nc_path, engine="h5netcdf")
print("wrote", nc_path, os.path.getsize(nc_path), "bytes")

report = {
    "region": {"lat_min": 59.05, "lat_max": 60.25, "lon_min": 21.25, "lon_max": 22.45},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2005-06-01", "end": "2005-08-31"},
    "events": [
        {"onset": "2005-06-18", "end": "2005-06-22"},
        {"onset": "2005-07-04", "end": "2005-07-21"},
    ],
    "complete": True,
    "caveats": ("Dataset has no 29 February values (no day-60 observations), so day 60 of the "
                "climatology/threshold relies solely on the specified fill (mean of days 59 and 61) "
                "before smoothing. The +-5-day baseline windows use spillover days 1991-12-27..1991-12-31 "
                "and 2003-01-01..2003-01-05 as specified, so values outside 1992-2002 also entered the pools. "
                "Grid is 0.02 deg: the region is covered by 60x60 cells (lat 59.06-60.24, lon 21.26-22.44), "
                "of which 3290 are sea cells (SST finite on every target day). Per-cell gap joining was "
                "implemented as 'join if all gap days are non-hot'; the alternative reading (join any 1-2-day "
                "gap) yields an identical mask for this period.")
}
json_path = os.path.join(outdir, "report.json")
with open(json_path, "w") as f:
    json.dump(report, f, indent=2)
print("wrote", json_path)

# verify by re-reading
ds2 = xr.open_dataset(nc_path, engine="h5netcdf")
print(ds2)
m = ds2.mhw.values
print("dtype:", m.dtype, "sum:", int(m.sum()), "matches:", np.array_equal(m, mask))
print(json.dumps(json.load(open(json_path)), indent=2)[:1200])
