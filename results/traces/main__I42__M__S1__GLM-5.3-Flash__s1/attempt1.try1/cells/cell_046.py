import numpy as np, h5py, json, os
import xarray as xr
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
# dataset coordinate values for the region
with h5py.File(f"{base}/sst_19920615.nc","r") as f:
    lat = f["latitude"][:]
    lon = f["longitude"][:]
lat_idx = np.where((lat >= 62.25-1e-6) & (lat <= 63.45+1e-6))[0]
lon_idx = np.where((lon >= 18.73-1e-6) & (lon <= 19.93+1e-6))[0]
lat_reg = lat[lat_idx[0]:lat_idx[-1]+1].astype(np.float32)
lon_reg = lon[lon_idx[0]:lon_idx[-1]+1].astype(np.float32)

mhw = np.load("/work/mhw_final_corr.npy")   # (92,60,60) bool
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
time_coord = np.array([np.datetime64(t, "ns") for t in target_dates])

os.makedirs("/work/output", exist_ok=True)
mhw_u8 = mhw.astype(np.uint8)
ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw_u8, {
        "long_name": "marine heatwave (per-cell MHW) mask",
        "flag_values": np.array([0,1], dtype=np.uint8),
        "flag_meanings": "not_in_mhw in_mhw",
        "units": "1"})},
    coords={
        "time": ("time", time_coord, {"long_name": "Time", "standard_name": "time", "axis": "T"}),
        "lat": ("lat", lat_reg, {"long_name": "latitude", "units": "degrees_north", "standard_name": "latitude", "axis": "Y"}),
        "lon": ("lon", lon_reg, {"long_name": "longitude", "units": "degrees_east", "standard_name": "longitude", "axis": "X"}),
    },
    attrs={
        "title": "Marine heatwave mask, Baltic Sea region, 2012-06-01 to 2012-08-31",
        "dataset_id": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
        "method": "per-cell MHW: hot = SST >= 90th-percentile baseline threshold (1992-2002, +/-5-day calendar windows, hazen quantile, day-60 filled from days 59/61, 31-day circular running mean); runs >= 5 hot days, gaps of 1-2 days joined",
    },
)
ds.to_netcdf("/work/output/mhw_mask.nc", engine="h5netcdf")
print("wrote /work/output/mhw_mask.nc")

report = {
    "region": {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [{"onset": "2012-08-15", "end": "2012-08-19"}],
    "complete": True,
    "caveats": ("Day-of-year thresholds/climatology come from baseline pools spanning 1991-12-27 to 2003-01-05 "
                "(baseline years 1992-2002 widened by the +/-5-calendar-day windows, per the specified method). "
                "Per-cell MHWs were detected over the target period only. The region contains 292 land/non-sea cells "
                "(masked 0); 3308 sea cells were analysed. Sea cells were required to have finite SST on every target day. "
                "One regional event found: 2012-08-15 to 2012-08-19, with 26 cells in a per-cell MHW on those days."),
}
with open("/work/output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote /work/output/report.json")

# verify by re-reading
ds2 = xr.open_dataset("/work/output/mhw_mask.nc", engine="h5netcdf")
print(ds2)
print("mhw dtype:", ds2.mhw.dtype, "sum:", int(ds2.mhw.values.sum()))
print("time:", ds2.time.values[0], "..", ds2.time.values[-1], "n=", ds2.time.size)
print("lat:", ds2.lat.values[0], ds2.lat.values[-1], "lon:", ds2.lon.values[0], ds2.lon.values[-1])
with open("/work/output/report.json") as f:
    print(json.dumps(json.load(f), indent=2)[:1500])
