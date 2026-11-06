
import xarray as xr
import numpy as np
import json
import os
from datetime import date, timedelta

# Create output directory
os.makedirs('output', exist_ok=True)

# Load data
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

region_lat = lat[lat_idx]
region_lon = lon[lon_idx]

target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_time = time[target_time_idx]

mhw_mask = np.load('/tmp/mhw_mask.npy')
print("mhw_mask shape:", mhw_mask.shape)
print("mhw_mask dtype:", mhw_mask.dtype)

# Convert to uint8 for output
mhw_uint8 = mhw_mask.astype(np.uint8)
print("mhw_uint8 shape:", mhw_uint8.shape, "dtype:", mhw_uint8.dtype)

# Create NetCDF output
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
ds_out['mhw'].attrs['units'] = '1'
ds_out['mhw'].attrs['long_name'] = 'Per-cell marine heatwave mask (1 = in MHW, 0 = not in MHW)'

# Write NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Now write report.json
# Event dates
def npdt_to_date(t):
    dt = t.astype('datetime64[D]').astype(object)
    return date(dt.year, dt.month, dt.day)

# Events: single event from day 0 to day 30
event_list = [
    {
        "onset": npdt_to_date(target_time[0]).isoformat(),
        "end": npdt_to_date(target_time[30]).isoformat()
    }
]

# Baseline analysed: 1991-12-27 to 2003-01-05 (the extended baseline period)
# Actually, let me reconsider. The baseline_analysed should be the first and last
# baseline day that the threshold and climatology used. The pools include dates
# from 1991-12-27 to 2003-01-05. So:
baseline_analysed = {
    "start": "1991-12-27",
    "end": "2003-01-05"
}

# Target analysed
target_analysed = {
    "start": npdt_to_date(target_time[0]).isoformat(),
    "end": npdt_to_date(target_time[-1]).isoformat()
}

report = {
    "region": {
        "lat_min": 64.39,
        "lat_max": 65.59,
        "lon_min": 23.41,
        "lon_max": 24.61
    },
    "baseline_analysed": baseline_analysed,
    "target_analysed": target_analysed,
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(report)
