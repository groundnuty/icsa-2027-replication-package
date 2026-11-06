
import fsspec
import numpy as np
import xarray as xr
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 132, 191
lon_start, lon_end = 436, 495

# Baseline dates: 1991-12-27 to 2003-01-05
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)
n_baseline = len(baseline_dates)
print(f"Baseline days: {n_baseline}")

# Load baseline data in chunks
# The full region is 60x60 per day, and we have 4028 days
# Total: 4028 * 60 * 60 * 8 bytes = ~116 MB in float64
# Let's load as float32 first then convert as needed
# Actually, let's just load it all

baseline_sst = np.zeros((n_baseline, 60, 60), dtype=np.float32)
for i, bd in enumerate(baseline_dates):
    fname = f"sst_{bd.strftime('%Y%m%d')}.nc"
    fpath = f"{base_dir}/{fname}"
    f = fs.open(fpath, "rb")
    ds = xr.open_dataset(f, engine="h5netcdf")
    baseline_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1].astype(np.float32)
    ds.close()
    f.close()
    if (i+1) % 500 == 0:
        print(f"Loaded {i+1}/{n_baseline} baseline days")

print(f"Baseline SST loaded, shape: {baseline_sst.shape}")
np.save('baseline_sst.npy', baseline_sst)
np.save('baseline_dates.npy', np.array([bd.toordinal() for bd in baseline_dates]))
