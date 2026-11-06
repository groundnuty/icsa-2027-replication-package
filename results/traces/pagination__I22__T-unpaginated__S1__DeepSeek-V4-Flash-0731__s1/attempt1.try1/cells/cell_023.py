
import numpy as np
import datetime
import json
import os
import xarray as xr

os.makedirs('output', exist_ok=True)

# Load target dates
target_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/target_dates.npy')]

# Since we've verified there are no MHWs, mhw_mask is all zeros
n_target = len(target_dates)
n_lat, n_lon = 60, 60

# Load region coordinates
# From our earlier reference: lat_idx = 196-255, lon_idx = 485-544
# Need to get the actual coordinate values
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

with fs.open(f'{base}/sst_20040601.nc', 'rb') as fh:
    ds = xr.open_dataset(fh, engine='h5netcdf')
    lat_full = ds['latitude'].values
    lon_full = ds['longitude'].values
    ds.close()

lat_idx = np.arange(196, 256)
lon_idx = np.arange(485, 545)
region_lat = lat_full[lat_idx]
region_lon = lon_full[lon_idx]

# Build time coordinate
time_vals = np.array([np.datetime64(d) for d in target_dates])

# Create mhw mask (all zeros since no MHWs)
mhw = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw),
    },
    coords={
        'time': time_vals,
        'lat': region_lat,
        'lon': region_lon,
    }
)

# Write NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print('Written output/mhw_mask.nc')
print(ds_out)

# Write report
report = {
    'region': {
        'lat_min': 57.41,
        'lat_max': 58.61,
        'lon_min': 18.69,
        'lon_max': 19.89
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2004-06-01',
        'end': '2004-08-31'
    },
    'events': [],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print('Written output/report.json')
print(json.dumps(report, indent=2))
