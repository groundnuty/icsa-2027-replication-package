
import numpy as np
import xarray as xr
import json
import os
import datetime

# Create output directory
os.makedirs('output', exist_ok=True)

# Load data
lat_idx = np.load('lat_idx.npy')
lon_idx = np.load('lon_idx.npy')
sea_cells = np.load('sea_cells.npy')
mhw_mask = np.load('mhw_mask.npy')

# Load the original dataset to get coordinate values
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
ds = xr.open_dataset(f'{data_dir}/sst_20070601.nc', engine='h5netcdf')
lat_region = ds['latitude'].values[lat_idx]
lon_region = ds['longitude'].values[lon_idx]
ds.close()

# Create time dimension for target period
target_dates = []
d = datetime.date(2007, 6, 1)
for i in range(92):
    target_dates.append(d)
    d += datetime.timedelta(days=1)
time_coords = np.array(target_dates, dtype='datetime64[ns]')

print(f"lat_region shape: {lat_region.shape}")
print(f"lon_region shape: {lon_region.shape}")
print(f"mhw_mask shape: {mhw_mask.shape}")
print(f"time_coords shape: {time_coords.shape}")

# Create the dataset
mhw_var = mhw_mask.astype(np.uint8)  # shape (92, 60, 60)

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_var)
    },
    coords={
        'time': time_coords,
        'lat': lat_region,
        'lon': lon_region
    }
)

# Save to NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Saved output/mhw_mask.nc")

# Create report.json
events = [{"onset": "2007-06-07", "end": "2007-06-14"}]

report = {
    "region": {
        "lat_min": 57.83,
        "lat_max": 59.03,
        "lon_min": 17.41,
        "lon_max": 18.61
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2007-06-01",
        "end": "2007-08-31"
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Saved output/report.json")
