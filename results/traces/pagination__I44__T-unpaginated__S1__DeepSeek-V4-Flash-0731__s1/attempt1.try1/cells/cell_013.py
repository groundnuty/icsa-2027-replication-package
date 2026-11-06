import fsspec
import xarray as xr
import numpy as np
from datetime import date, timedelta
import pickle
import os

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

region_lat = lat[lat_start:lat_end]
region_lon = lon[lon_start:lon_end]
n_lat = len(region_lat)
n_lon = len(region_lon)
print(f"Region: {n_lat} x {n_lon} = {n_lat*n_lon} cells")

# Load all baseline dates: 1991-12-27 to 2003-01-05
start_date = date(1991, 12, 27)
end_date = date(2003, 1, 5)

all_loaded_dates = []
current = start_date
while current <= end_date:
    all_loaded_dates.append(current)
    current += timedelta(days=1)

n_days = len(all_loaded_dates)
print(f"Loading {n_days} baseline days for region...")

# Load all baseline data
baseline_sst = np.full((n_days, n_lat, n_lon), np.nan, dtype=np.float64)

for i, d in enumerate(all_loaded_dates):
    fname = f"icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    try:
        with fs.open(fname, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            sst = ds['analysed_sst'].values[0, lat_start:lat_end, lon_start:lon_end]
            baseline_sst[i] = sst.astype(np.float64)
            ds.close()
    except Exception as e:
        print(f"Error loading {fname}: {e}")
    
    if (i+1) % 1000 == 0:
        print(f"  Loaded {i+1}/{n_days}")

print(f"Done loading baseline data. Shape: {baseline_sst.shape}")

# Save to disk
os.makedirs('/tmp/work', exist_ok=True)
np.save('/tmp/work/baseline_sst.npy', baseline_sst)

# Save dates as pickled list
with open('/tmp/work/all_loaded_dates.pkl', 'wb') as f:
    pickle.dump(all_loaded_dates, f)

# Save region info
np.save('/tmp/work/region_lat.npy', region_lat)
np.save('/tmp/work/region_lon.npy', region_lon)
with open('/tmp/work/region_bounds.pkl', 'wb') as f:
    pickle.dump((lat_start, lat_end, lon_start, lon_end), f)

print("Saved baseline data and metadata.")
