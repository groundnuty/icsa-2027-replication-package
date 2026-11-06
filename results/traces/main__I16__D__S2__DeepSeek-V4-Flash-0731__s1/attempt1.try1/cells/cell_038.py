
import numpy as np
import xarray as xr
from datetime import date, timedelta
from bisect import bisect_left, bisect_right
from collections import defaultdict
import json
import os

def day_of_year(month, day):
    """Map (month, day) to day of year 1-366 (366-day abstract calendar)."""
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

def smooth_31(arr):
    """Smooth along axis 0 with 31-day centred moving average wrapping around (mod 366)."""
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    from numpy.lib.stride_tricks import sliding_window_view
    windows = sliding_window_view(padded, 31, axis=0)
    return np.mean(windows, axis=-1)

# === Parameters ===
REGION = {"lat_min": 56.63, "lat_max": 57.83, "lon_min": 20.23, "lon_max": 21.43}
TARGET_START = "2008-06-01"
TARGET_END = "2008-08-31"

# === Load dataset ===
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_all = ds.latitude.values
lon_all = ds.longitude.values
time_all = ds.time.values

# Region indices
lat_idx = np.where((lat_all >= REGION["lat_min"]) & (lat_all <= REGION["lat_max"]))[0]
lon_idx = np.where((lon_all >= REGION["lon_min"]) & (lon_all <= REGION["lon_max"]))[0]
print(f"Region cells: {len(lat_idx)} lat x {len(lon_idx)} lon")

# Baseline data range (with window days)
b_start = np.where(time_all >= np.datetime64('1991-12-27'))[0][0]
b_end = np.where(time_all <= np.datetime64('2003-01-05'))[0][-1]
print(f"Baseline data indices: {b_start} to {b_end}")

# Load baseline region data
baseline_region = ds['analysed_sst'].isel(time=slice(b_start, b_end+1),
                                          latitude=lat_idx, longitude=lon_idx).load()
baseline_data = baseline_region.values.astype(np.float64)  # (4028, 60, 60)
n_baseline = baseline_data.shape[0]
print(f"Baseline data shape: {baseline_data.shape}")

# Target data range
t_start = np.where(time_all >= np.datetime64(TARGET_START))[0][0]
t_end = np.where(time_all <= np.datetime64(TARGET_END))[0][-1]
print(f"Target data indices: {t_start} to {t_end}")

target_region = ds['analysed_sst'].isel(time=slice(t_start, t_end+1),
                                        latitude=lat_idx, longitude=lon_idx).load()
target_data = target_region.values.astype(np.float64)  # (92, 60, 60)
n_target = target_data.shape[0]
target_times = target_region.time.values
print(f"Target data shape: {target_data.shape}")
print(f"Target times: {str(target_times[0])[:10]} to {str(target_times[-1])[:10]}")

# === Identify sea cells ===
sea_mask = np.all(np.isfinite(target_data), axis=0)
print(f"Sea cells: {np.sum(sea_mask)} out of {sea_mask.size}")

# === Build day-of-year pools for baseline ===
# Baseline dates
base_times = baseline_region.time.values
base_dates = [date(1970,1,1) + timedelta(days=int((t - np.datetime64('1970-01-01')) / np.timedelta64(1,'D'))) 
              for t in base_times]

# Baseline years 1992-2002
base_start_date = date(1992,1,1)
base_end_date = date(2002,12,31)

# Build list of baseline dates with doy
base_info = [(B, day_of_year(B.month, B.day)) for B in base_dates 
             if base_start_date <= B <= base_end_date]
base_date_list = [x[0] for x in base_info]

# For each date D in the baseline+window range, find which pools it contributes to
D_to_pools = {}
for i, D in enumerate(base_dates):
    lo = bisect_left(base_date_list, D - timedelta(days=5))
    hi = bisect_right(base_date_list, D + timedelta(days=5))
    pools = set()
    for j in range(lo, hi):
        pools.add(base_info[j][1])
    D_to_pools[i] = pools

# Group time indices by doy
doy_to_timeidx = defaultdict(list)
for i, pools in D_to_pools.items():
    for d in pools:
        if d != 60:
            doy_to_timeidx[d].append(i)

print(f"Number of doys with pools: {len(doy_to_timeidx)}")

# === Compute threshold and climatology ===
n_lat = len(lat_idx)
n_lon = len(lon_idx)
threshold = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for d, tidx in doy_to_timeidx.items():
    pool_data = baseline_data[tidx, :, :]
    threshold[d-1, :, :] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
    climatology[d-1, :, :] = np.nanmean(pool_data, axis=0)

# Set day 60 to mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

print(f"Day 60 set to mean of 59 and 61")

# === Smooth ===
threshold_smooth = smooth_31(threshold)
climatology_smooth = smooth_31(climatology)

print(f"Smoothed threshold shape: {threshold_smooth.shape}")

# Verify all sea cells have finite smoothed threshold
ts_flat = threshold_smooth.reshape(366, -1)
sea_flat = sea_mask.ravel()
sea_ts = ts_flat[:, sea_flat]
nan_in_sea = np.any(np.isnan(sea_ts), axis=0)
print(f"Sea cells with NaN in smoothed threshold: {np.sum(nan_in_sea)}")

# === Target day-of-year mapping ===
target_dates = [date(1970,1,1) + timedelta(days=int((t - np.datetime64('1970-01-01')) / np.timedelta64(1,'D'))) 
                for t in target_times]
target_doys = np.array([day_of_year(d.month, d.day) for d in target_dates])
print(f"Target doys: {target_doys[0]} to {target_doys[-1]}")

# === Hot days ===
thresh_for_target = threshold_smooth[target_doys - 1]  # (92, 60, 60)
hot = np.zeros_like(target_data, dtype=bool)
hot[:, sea_mask] = target_data[:, sea_mask] >= thresh_for_target[:, sea_mask]
print(f"Hot cell-days: {np.sum(hot)}")

# === Per-cell MHWs ===
mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for ilat in range(n_lat):
    for ilon in range(n_lon):
        if not sea_mask[ilat, ilon]:
            continue
        h = hot[:, ilat, ilon]
        
        # Find runs of consecutive hot days
        runs = []
        i = 0
        while i < n_target:
            if h[i]:
                start = i
                while i < n_target and h[i]:
                    i += 1
                runs.append((start, i-1))
            else:
                i += 1
        
        # Keep runs of length >= 5
        mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join MHWs separated by 1 or 2 non-hot days
        if mhw_runs:
            joined = [mhw_runs[0]]
            for r in mhw_runs[1:]:
                prev_end = joined[-1][1]
                gap = r[0] - prev_end - 1
                if 1 <= gap <= 2:
                    joined[-1] = (joined[-1][0], r[1])
                else:
                    joined.append(r)
            
            for start, end in joined:
                mhw_mask[start:end+1, ilat, ilon] = 1

print(f"Cells with MHW: {np.sum(np.any(mhw_mask, axis=0))}")
print(f"Total mhw cell-days: {np.sum(mhw_mask)}")

# === Regional events ===
active = np.any(mhw_mask, axis=(1, 2))  # (92,)
print(f"Active days: {np.where(active)[0]}")

# Find maximal runs of active days
events = []
i = 0
while i < n_target:
    if active[i]:
        start = i
        while i < n_target and active[i]:
            i += 1
        events.append((start, i-1))
    else:
        i += 1

event_list = []
for e_start, e_end in events:
    onset = str(target_times[e_start])[:10]
    end = str(target_times[e_end])[:10]
    event_list.append({"onset": onset, "end": end})
    print(f"Event: {onset} to {end}")

# === Save results ===
print("\n=== Writing output files ===")

# Create output directory
os.makedirs('output', exist_ok=True)

# Write NetCDF
# Use dataset coordinates for the region and target period
lat_region = lat_all[lat_idx]
lon_region = lon_all[lon_idx]
time_target = target_times

out_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_target,
        'lat': lat_region,
        'lon': lon_region,
    }
)
out_ds['mhw'].attrs['long_name'] = 'marine heatwave mask'
out_ds['mhw'].attrs['units'] = '1 = in MHW, 0 = not in MHW'
out_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": REGION["lat_min"],
        "lat_max": REGION["lat_max"],
        "lon_min": REGION["lon_min"],
        "lon_max": REGION["lon_max"]
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2008-06-01",
        "end": "2008-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Written output/report.json")

print("\nReport:")
print(json.dumps(report, indent=2))
