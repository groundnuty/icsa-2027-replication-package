
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import time

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544

# Generate target dates
target_start = dt.date(2017, 6, 1)
target_end = dt.date(2017, 8, 31)

dates_target = []
d = target_start
while d <= target_end:
    dates_target.append(d)
    d += dt.timedelta(days=1)

print(f"Loading {len(dates_target)} target files...")
start = time.time()

target_sst = np.full((len(dates_target), 60, 60), np.nan, dtype=np.float64)
for i, date in enumerate(dates_target):
    fname = f"sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc"
    f = fs.open(f'{base_path}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    target_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1].astype(np.float64)
    ds.close()

elapsed = time.time() - start
print(f"Loaded {len(dates_target)} target files in {elapsed:.1f}s")
print(f"Target SST shape: {target_sst.shape}")
print(f"NaN fraction: {np.isnan(target_sst).mean():.4f}")

# Check which cells are sea cells (finite on every target day)
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {60*60}")
