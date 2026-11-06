
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import xarray as xr

# Load data
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_time = np.load('/tmp/target_time.npy')
region_lat = np.load('/tmp/region_lat.npy')
region_lon = np.load('/tmp/region_lon.npy')
hot = np.load('/tmp/hot.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

# Verify mhw_mask
print("mhw_mask shape:", mhw_mask.shape)
print("mhw_mask dtype:", mhw_mask.dtype)
print("mhw_mask sum:", mhw_mask.sum())

# Regional events
active = mhw_mask.any(axis=(1, 2))
events = []
i = 0
n_time = len(target_dates)
while i < n_time:
    if active[i]:
        start = i
        while i < n_time and active[i]:
            i += 1
        end = i - 1
        events.append({
            "onset": target_dates[start].strftime('%Y-%m-%d'),
            "end": target_dates[end].strftime('%Y-%m-%d')
        })
    else:
        i += 1

print("Events:", events)

# Create output directory
os.makedirs('output', exist_ok=True)

# Create NetCDF output
# mhw is uint8, dimensions (time, lat, lon)
# Use the dataset's coordinate values

# Convert mhw_mask to uint8
mhw_uint8 = mhw_mask.astype(np.uint8)

# Create xarray Dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'latitude', 'longitude'), mhw_uint8)
    },
    coords={
        'time': target_time,
        'latitude': region_lat,
        'longitude': region_lon
    }
)

# Add attributes
ds_out['mhw'].attrs['long_name'] = 'Marine heatwave mask'
ds_out['mhw'].attrs['units'] = '1 = inside per-cell MHW, 0 = outside'

# Save
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Saved mhw_mask.nc")

# Create report
report = {
    "region": {
        "lat_min": 58.69,
        "lat_max": 59.89,
        "lon_min": 18.69,
        "lon_max": 19.89
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2010-06-01",
        "end": "2010-08-31"
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Saved report.json")
print("Report:", json.dumps(report, indent=2))
