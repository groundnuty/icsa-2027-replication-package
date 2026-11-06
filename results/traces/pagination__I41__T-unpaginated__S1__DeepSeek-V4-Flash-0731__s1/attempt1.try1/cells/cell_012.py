
import fsspec
import xarray as xr
import numpy as np
import datetime
import time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check if we need to re-load baseline or if we can continue
# We need to reload baseline data since this is a fresh sandbox call
# Let's just proceed with the target data first and then build the full script

# Target dates
target_start = datetime.date(2021, 6, 1)
target_end = datetime.date(2021, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)
n_target = len(target_dates)
print(f"Target dates: {n_target}")

# Load target data
lat_min_i, lat_max_i = 404, 463
lon_min_i, lon_max_i = 559, 618

target_data = np.zeros((n_target, 60, 60), dtype=np.float32)
t0 = time.time()
for i, date in enumerate(target_dates):
    fpath = f'{base}/sst_{date.strftime("%Y%m%d")}.nc'
    f = fs.open(fpath, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    target_data[i] = ds.analysed_sst.values[0, lat_min_i:lat_max_i+1, lon_min_i:lon_max_i+1]
    ds.close()
    f.close()

print(f"Target data loaded in {time.time()-t0:.1f}s")
print(f"Target data shape: {target_data.shape}")
print(f"NaN count: {np.isnan(target_data).sum()}")
