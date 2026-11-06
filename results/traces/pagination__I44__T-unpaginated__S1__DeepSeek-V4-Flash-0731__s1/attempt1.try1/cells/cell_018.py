import fsspec
import xarray as xr
import numpy as np
from datetime import date, timedelta
import pickle

fs = fsspec.filesystem('onedata')

# Load region bounds
with open('/tmp/work/region_bounds.pkl', 'rb') as f:
    lat_start, lat_end, lon_start, lon_end = pickle.load(f)

print(f"Region indices: lat {lat_start}-{lat_end-1}, lon {lon_start}-{lon_end-1}")

# Load target dates: 2004-06-01 to 2004-08-31
target_start = date(2004, 6, 1)
target_end = date(2004, 8, 31)

target_dates = []
current = target_start
while current <= target_end:
    target_dates.append(current)
    current += timedelta(days=1)

print(f"Target dates: {len(target_dates)} from {target_dates[0]} to {target_dates[-1]}")

n_target = len(target_dates)
n_lat = lat_end - lat_start
n_lon = lon_end - lon_start

# Load target SST data
target_sst = np.full((n_target, n_lat, n_lon), np.nan, dtype=np.float64)

for i, d in enumerate(target_dates):
    fname = f"icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    try:
        with fs.open(fname, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            sst = ds['analysed_sst'].values[0, lat_start:lat_end, lon_start:lon_end]
            target_sst[i] = sst.astype(np.float64)
            ds.close()
    except Exception as e:
        print(f"Error loading {fname}: {e}")

print(f"Target SST shape: {target_sst.shape}")

# Determine sea cells: cells with finite SST on every day of target period
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# Save target data
np.save('/tmp/work/target_sst.npy', target_sst)
with open('/tmp/work/target_dates.pkl', 'wb') as f:
    pickle.dump(target_dates, f)
np.save('/tmp/work/sea_cells.npy', sea_cells)

print("Saved target data.")
