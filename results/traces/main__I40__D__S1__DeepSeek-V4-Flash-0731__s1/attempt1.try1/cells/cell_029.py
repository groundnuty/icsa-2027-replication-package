
import numpy as np
import pandas as pd
import json
import xarray as xr
import os

# Load data
target_sst = np.load('/work/target_sst.npy')
targ_times = np.load('/work/targ_times.npy')
thresholds = np.load('/work/thresholds.npy')

targ_dates = pd.DatetimeIndex(targ_times)
n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
n_targ = len(targ_dates)

# Day of year mapping
def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

targ_doy = np.array([date_to_doy(d) for d in targ_dates])

# Sea cells
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if np.all(np.isfinite(target_sst[:, i, j])):
            sea_cells[i, j] = True

# Determine hot days per cell
hot = np.zeros((n_targ, n_lat, n_lon), dtype=bool)

for t in range(n_targ):
    d = targ_doy[t]
    thr = thresholds[d-1, :, :]
    sst_t = target_sst[t, :, :].astype(np.float64)
    hot[t] = (sst_t >= thr) & sea_cells & np.isfinite(sst_t) & np.isfinite(thr)

# Find per-cell MHWs
mhw_mask = np.zeros((n_targ, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        hot_series = hot[:, i, j]
        runs = []
        t = 0
        while t < n_targ:
            if hot_series[t]:
                start = t
                while t < n_targ and hot_series[t]:
                    t += 1
                end = t - 1
                runs.append((start, end))
            else:
                t += 1
        if len(runs) == 0:
            continue
        joined = [list(runs[0])]
        for k in range(1, len(runs)):
            gap = runs[k][0] - joined[-1][1] - 1
            if gap <= 2:
                joined[-1][1] = runs[k][1]
            else:
                joined.append(list(runs[k]))
        for start, end in joined:
            if end - start + 1 >= 5:
                mhw_mask[start:end+1, i, j] = True

# Regional events
active = mhw_mask.any(axis=(1, 2))
events = []
t = 0
while t < n_targ:
    if active[t]:
        start = t
        while t < n_targ and active[t]:
            t += 1
        end = t - 1
        events.append((start, end))
    else:
        t += 1

event_list = []
for start, end in events:
    event_list.append({
        "onset": targ_dates[start].strftime('%Y-%m-%d'),
        "end": targ_dates[end].strftime('%Y-%m-%d')
    })

print(f"Events: {event_list}")
print(f"MHW mask shape: {mhw_mask.shape}, dtype: {mhw_mask.dtype}")
print(f"MHW mask sum: {mhw_mask.sum()}")

# Get coordinates from the original dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 61.57) & (lat_vals <= 62.77)
lon_mask = (lon_vals >= 20.17) & (lon_vals <= 21.37)
region_lat = lat_vals[lat_mask]
region_lon = lon_vals[lon_mask]

# Target time values
times = ds.time.values
targ_mask = (times >= np.datetime64('2009-06-01')) & (times <= np.datetime64('2009-08-31'))
targ_time_vals = times[targ_mask]

# Write the NetCDF file
os.makedirs('output', exist_ok=True)

# Create the dataset
# mhw has shape (time, lat, lon), uint8
mhw_uint8 = mhw_mask.astype(np.uint8)

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_uint8)
    },
    coords={
        'time': targ_time_vals,
        'lat': region_lat,
        'lon': region_lon
    }
)

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Write the report
report = {
    "region": {
        "lat_min": 61.57,
        "lat_max": 62.77,
        "lon_min": 20.17,
        "lon_max": 21.37
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2009-06-01",
        "end": "2009-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(f"Report: {json.dumps(report, indent=2)}")

# Verify the output files
print("\nVerifying output files:")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")

ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"mhw variable shape: {ds_check.mhw.shape}")
print(f"mhw dtype: {ds_check.mhw.dtype}")
print(f"mhw time: {ds_check.time.values[0]} to {ds_check.time.values[-1]}")
print(f"mhw lat: {ds_check.lat.values[0]} to {ds_check.lat.values[-1]}")
print(f"mhw lon: {ds_check.lon.values[0]} to {ds_check.lon.values[-1]}")
print(f"mhw sum: {ds_check.mhw.values.sum()}")

with open('output/report.json') as f:
    report_check = json.load(f)
print(f"\nReport check: {json.dumps(report_check, indent=2)}")
