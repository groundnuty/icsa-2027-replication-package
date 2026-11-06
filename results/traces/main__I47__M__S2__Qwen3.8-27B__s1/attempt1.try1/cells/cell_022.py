import numpy as np, json
import xarray as xr

m = np.load("work/mhw.npz")
mhw_flat = m["mhw"]                      # (92, n_sea)
tgt_dates = m["tgt_dates"]               # datetime64[D] (92)
st = np.load("work/stats.npz")
sea_idx = st["sea_idx"]
z = np.load("work/sst.npz", allow_pickle=False)
lat = z["lat"]; lon = z["lon"]
nlat, nlon = lat.size, lon.size

finite_all = np.zeros((nlat, nlon), dtype=bool)
finite_all.ravel()[sea_idx] = True

mhw3 = np.zeros((mhw_flat.shape[0], nlat, nlon), dtype=np.uint8)
mhw3[:, finite_all.ravel()] = mhw_flat.astype(np.uint8)
print("mhw3 shape:", mhw3.shape, "ones:", int(mhw3.sum()),
      "matches flat:", bool((mhw3[:, finite_all.ravel()] == mhw_flat.astype(np.uint8)).all()))

time_ns = tgt_dates.astype("datetime64[ns]")
da = xr.DataArray(
    mhw3,
    dims=("time", "latitude", "longitude"),
    coords={
        "time": ("time", time_ns),
        "latitude": ("latitude", lat.astype(np.float32)),
        "longitude": ("longitude", lon.astype(np.float32)),
    },
    name="mhw",
    attrs={"description": "1 = grid cell inside a per-cell marine heatwave on that day, 0 otherwise (land cells 0). "
                          "Region 64.39-65.59N, 23.41-24.61E; period 2019-06-01..2019-08-31."}
)
da.time.attrs["units"] = "days since 1982-01-01"  # informational; values stored as datetime64
ds_out = da.to_dataset()
ds_out.to_netcdf("output/mhw_mask.nc")
print("wrote output/mhw_mask.nc")

# quick re-read check
chk = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(chk)
print("mhw dtype:", chk["mhw"].dtype, "sum:", int(chk["mhw"].values.sum()))
print("time first/last:", chk["time"].values[0], chk["time"].values[-1])
chk.close()

events = json.load(open("work/events.json"))
report = {
    "region": {"lat_min": 64.39, "lat_max": 65.59, "lon_min": 23.41, "lon_max": 24.61},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
    "events": [{"onset": s, "end": e} for s, e in events],
    "complete": True,
    "caveats": "Sea cells (3311 of 3600 region cells) are those with finite SST on every day 2019-06-01..2019-08-31; "
               "land/missing cells are 0 in the mask. Thresholds/climatology per day of year from 1992-2002 baselines "
               "using +/-5 calendar-day windows (1991-12-27..2003-01-05 included), 90th percentile (hazen), day 60 filled "
               "from days 59 and 61, then 31-day centred circular moving-mean smoothing. A day is hot when SST (K) >= "
               "smoothed threshold; per-cell MHWs are runs of >=5 hot days, merged when separated by 1-2 non-hot days; "
               "regional events are maximal runs of days with at least one cell in an MHW.",
}
json.dump(report, open("output/report.json", "w"), indent=2)
print("wrote output/report.json")
print(json.dumps(report, indent=2))
