
import fsspec
import xarray as xr
import numpy as np
import datetime
import time
import pickle

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 48, 108  # inclusive range: 48 to 107
lon_start, lon_end = 353, 413  # inclusive range: 353 to 412

def doy_from_date(date):
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

# Extended range dates
ext_start = datetime.date(1991, 12, 27)
ext_end = datetime.date(2003, 1, 5)
ext_dates = []
d = ext_start
while d <= ext_end:
    ext_dates.append(d)
    d += datetime.timedelta(days=1)

print(f"Loading {len(ext_dates)} baseline files...")
start = time.time()

# Load all baseline data
baseline_sst = np.zeros((len(ext_dates), lat_end-lat_start, lon_end-lon_start), dtype=np.float32)
date_indices = {}  # date string -> index in baseline_sst

for i, date in enumerate(ext_dates):
    date_str = date.strftime('%Y%m%d')
    date_indices[date_str] = i
    path = f'{base}/sst_{date_str}.nc'
    with fs.open(path, 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        baseline_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end, lon_start:lon_end]

elapsed = time.time() - start
print(f"Loaded {len(ext_dates)} files in {elapsed:.1f}s ({elapsed/60:.1f} min)")
print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"NaN count: {np.isnan(baseline_sst).sum()}")

# Save the data
np.save('/tmp/baseline_sst.npy', baseline_sst)
with open('/tmp/date_indices.pkl', 'wb') as f:
    pickle.dump(date_indices, f)
with open('/tmp/ext_dates.pkl', 'wb') as f:
    pickle.dump([d.strftime('%Y%m%d') for d in ext_dates], f)

print("Saved baseline data")
