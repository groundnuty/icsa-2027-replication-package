import fsspec
import xarray as xr
import numpy as np
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')

# Region bounds
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

# Grid indices
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    lat_start = np.where(lat >= lat_min)[0][0]
    lat_end = np.where(lat <= lat_max)[0][-1] + 1
    lon_start = np.where(lon >= lon_min)[0][0]
    lon_end = np.where(lon <= lon_max)[0][-1] + 1

# Define all baseline dates: 1991-12-27 to 2003-01-05
start_date = date(1991, 12, 27)
end_date = date(2003, 1, 5)

all_dates = []
current = start_date
while current <= end_date:
    all_dates.append(current)
    current += timedelta(days=1)

print(f"Loading {len(all_dates)} baseline days for region...")

# Load all data
n_lat = lat_end - lat_start
n_lon = lon_end - lon_start
baseline_sst = np.full((len(all_dates), n_lat, n_lon), np.nan, dtype=np.float64)
baseline_dates = []

for i, d in enumerate(all_dates):
    fname = f"icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    try:
        with fs.open(fname, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            sst = ds['analysed_sst'].values[0, lat_start:lat_end, lon_start:lon_end]
            baseline_sst[i] = sst.astype(np.float64)
            baseline_dates.append(d)
            ds.close()
    except Exception as e:
        print(f"Error loading {fname}: {e}")
        baseline_sst[i] = np.nan
        baseline_dates.append(d)
    
    if (i+1) % 500 == 0:
        print(f"  Loaded {i+1}/{len(all_dates)}")

print(f"Done loading. Shape: {baseline_sst.shape}")
print(f"Finite values: {np.isfinite(baseline_sst).sum()}")
