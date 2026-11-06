
import numpy as np
import pickle
import json
import xarray as xr
import datetime as dt
import os

# ============================================================
# Load all state
# ============================================================
sea_cells = np.load('/work/sea_cells.npy')
target_sst = np.load('/work/target_sst.npy')
threshold_smoothed = np.load('/work/threshold_smoothed.npy')
climatology_smoothed = np.load('/work/climatology_smoothed.npy')
mhw_mask = np.load('/work/mhw_mask.npy')

with open('/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
with open('/work/events.pkl', 'rb') as f:
    events = pickle.load(f)
lats = np.load('/work/lats.npy')
lons = np.load('/work/lons.npy')

# ============================================================
# Region specification
# ============================================================
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45

# ============================================================
# Write output/mhw_mask.nc
# ============================================================
os.makedirs('output', exist_ok=True)

# Create xarray dataset
time_coords = np.array([np.datetime64(d) for d in target_dates])
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_coords,
        'lat': lats,
        'lon': lons
    }
)
ds_out['mhw'].attrs['long_name'] = 'marine heatwave mask'
ds_out['mhw'].attrs['units'] = '1 = inside MHW, 0 = outside MHW'

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")

# ============================================================
# Write output/report.json
# ============================================================
report = {
    'region': {
        'lat_min': lat_min,
        'lat_max': lat_max,
        'lon_min': lon_min,
        'lon_max': lon_max
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2014-06-01',
        'end': '2014-08-31'
    },
    'events': [
        {'onset': str(target_dates[s].date()), 'end': str(target_dates[e].date())}
        for s, e in events
    ],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Written output/report.json")
print(json.dumps(report, indent=2))
