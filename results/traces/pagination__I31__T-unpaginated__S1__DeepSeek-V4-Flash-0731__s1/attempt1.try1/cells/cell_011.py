
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import time

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544

# Generate all baseline dates
baseline_start = dt.date(1991, 12, 27)
baseline_end = dt.date(2003, 1, 5)

dates_baseline = []
d = baseline_start
while d <= baseline_end:
    dates_baseline.append(d)
    d += dt.timedelta(days=1)

print(f"Loading {len(dates_baseline)} baseline files...")
start = time.time()

# Load all baseline data
baseline_sst = np.full((len(dates_baseline), 60, 60), np.nan, dtype=np.float64)
for i, date in enumerate(dates_baseline):
    fname = f"sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc"
    f = fs.open(f'{base_path}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    baseline_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1].astype(np.float64)
    ds.close()
    if (i+1) % 500 == 0:
        elapsed = time.time() - start
        print(f"  Loaded {i+1}/{len(dates_baseline)} files, elapsed {elapsed:.1f}s")

elapsed = time.time() - start
print(f"Loaded all {len(dates_baseline)} baseline files in {elapsed:.1f}s")
print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"NaN fraction: {np.isnan(baseline_sst).mean():.4f}")
