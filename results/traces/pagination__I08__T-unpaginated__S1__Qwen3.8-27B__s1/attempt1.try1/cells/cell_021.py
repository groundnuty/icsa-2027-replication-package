
import numpy as np, datetime, json
import fsspec, xarray as xr

fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
mask = np.load('work/mask.npy')  # (92,60,60) uint8
sea = np.load('work/sea.npy')
ev_list = json.load(open('work/events.json'))

with fs.open(base + '/sst_20070601.nc', "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    lat = ds['latitude'].values[66:126]   # float32, dataset values
    lon = ds['longitude'].values[531:591] # float32, dataset values
    print("lat[0], lat[-1]:", lat[0], lat[-1], "| lon[0], lon[-1]:", lon[0], lon[-1])
    ds.close()

tdates = [datetime.date(2007,6,1) + datetime.timedelta(days=k) for k in range(92)]
time = np.array([d.isoformat() for d in tdates], dtype='datetime64[ns]')

da = xr.DataArray(mask, dims=('time','lat','lon'),
                  coords={'time': time, 'lat': lat, 'lon': lon}, name='mhw')
da.to_netcdf('output/mhw_mask.nc')

chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
assert chk['mhw'].dtype == np.uint8
assert tuple(chk['mhw'].shape) == (92, 60, 60)
assert int(chk['mhw'].sum()) == int(mask.sum())
sea2d = sea
print("land cells all zero:", bool((mask[:, ~sea2d] == 0).all()))

report = {
    "region": {"lat_min": 54.81, "lat_max": 56.01, "lon_min": 19.61, "lon_max": 20.81},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2007-06-01", "end": "2007-08-31"},
    "events": ev_list,
    "complete": True,
    "caveats": (
        "Baseline pools (per day of year) collected SST from every date within +/-5 calendar days of the "
        "1992-01-01..2002-12-31 baseline dates, so the extended days 1991-12-27..1991-12-31 and "
        "2003-01-01..2003-01-05 were included, as specified; reported as baseline_analysed start/end. "
        "Day of year uses the fixed calendar mapping (29 Feb = 60, Dec 31 = 366). Threshold = 90th "
        "percentile of each pool with numpy method='hazen' (0-based index n*p-0.5, NaNs ignored); "
        "climatology = pool mean (NaNs ignored); day 60 set to the mean of days 59 and 61; then both "
        "arrays (366 days) smoothed with a centred unweighted 31-day moving mean wrapping the year. "
        "Region contains 3600 grid cells (60x60); 311 cells with non-finite SST on at least one target "
        "day (land) were excluded from the analysis and set to 0 in the mask; the remaining 3289 sea "
        "cells had finite SST on all 92 target days and finite smoothed thresholds throughout the target "
        "window. All 92 target days (2007-06-01..2007-08-31) were available and analysed. One regional "
        "event (2007-06-01..2007-06-27) begins on the first target day; per the method, MHW detection "
        "used target-period days only."
    )
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("files written")
print(open('output/report.json').read()[:800])
