
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, time, json

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
intermediate_dir = 'intermediate'

# Load metadata
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

target_dates = [date.fromisoformat(d) for d in meta['target_dates']]
baseline_dates = [date.fromisoformat(d) for d in meta['baseline_dates']]
lat_idx = np.load(f'{intermediate_dir}/lat_idx.npy')
lon_idx = np.load(f'{intermediate_dir}/lon_idx.npy')

# Load baseline data
baseline_sst = np.load(f'{intermediate_dir}/baseline_sst.npy')
print(f"Baseline data loaded: {baseline_sst.shape}")

# Load target data
target_sst = np.full((len(target_dates), len(lat_idx), len(lon_idx)), np.nan, dtype=np.float32)
print("Loading target data...")
t0 = time.time()
for i, dt in enumerate(target_dates):
    fname = f'{data_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(fname, engine='h5netcdf')
    target_sst[i] = ds.analysed_sst.values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    ds.close()
print(f"Target loaded in {time.time()-t0:.1f}s")

np.save(f'{intermediate_dir}/target_sst.npy', target_sst)

# Identify sea cells
sea_cells = ~np.isnan(target_sst).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")
np.save(f'{intermediate_dir}/sea_cells.npy', sea_cells)

print("All data saved")
