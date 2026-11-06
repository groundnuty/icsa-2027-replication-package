
import numpy as np, json, xarray as xr, fsspec
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
lat_full = ds['latitude'].values; lon_full = ds['longitude'].values
t_sample = ds['time'].values
ds.close(); f.close()

lat = lat_full[545:605].astype(np.float32)
lon = lon_full[721:781].astype(np.float32)

def get_dates(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out
tgt_dates = get_dates(date(2019,6,1), date(2019,8,31))
time_coord = np.array([d.strftime('%Y-%m-%dT00:00:00') for d in tgt_dates], dtype='datetime64[ns]')
assert time_coord[0] == t_sample[0] and str(time_coord[0]) == '2019-06-01T00:00:00'

mhw_cell = np.load('/work/mhw_cell.npy')          # (92, 3311)
sea = np.load('/work/sea.npy').reshape(60, 60)
mhw = np.zeros((92, 60, 60), dtype=np.uint8)
mhw[:, sea] = mhw_cell.T.astype(np.uint8)
print("mhw sum:", int(mhw.sum()), "== cell mhw sum:", int(mhw_cell.sum()))

out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw, {"long_name": "marine heatwave mask (1 = inside per-cell MHW, 0 otherwise)"})},
    coords={
        "time": ("time", time_coord, {"standard_name": "time", "calendar": "standard"}),
        "latitude": ("latitude", lat, {"units": "degrees_north", "standard_name": "latitude"}),
        "longitude": ("longitude", lon, {"units": "degrees_east", "standard_name": "longitude"}),
    },
)
out.to_netcdf('/work/output/mhw_mask.nc', engine="netcdf4")
print("wrote mhw_mask.nc")

inter = json.load(open('/work/intermediate.json'))
report = {
    "region": {"lat_min": 64.39, "lat_max": 65.59, "lon_min": 23.41, "lon_max": 24.61},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
    "events": [{"onset": e["onset"], "end": e["end"]} for e in inter["events"]],
    "complete": True,
    "caveats": ("Thresholds/climatology from 1992-2002 baseline day-of-year pools, where each pool includes every SST value within +/-5 calendar days of a baseline date; "
                "per the method this extends to buffer days 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. 90th percentile computed with numpy method='hazen' "
                "(MATLAB quantile default, Hyndman-Fan type 5); day-60 values set to the mean of days 59 and 61 before a 31-day centred circular moving mean. "
                "Region resolved on the dataset's 0.02 deg grid: lat 64.40-65.58 N, lon 23.42-24.60 E (3600 cells, 3311 sea cells finite on all 92 target days). "
                "Hot-day test: SST in kelvin (float32 as stored, compared in float64) >= cell threshold for that day of year."),
}
json.dump(report, open('/work/output/report.json', 'w'), indent=2)
print("wrote report.json")
