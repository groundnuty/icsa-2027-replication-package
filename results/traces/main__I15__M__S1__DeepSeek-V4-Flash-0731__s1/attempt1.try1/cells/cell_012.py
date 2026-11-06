import numpy as np
from datetime import datetime, timedelta
import xarray as xr

# Load indices
lat_idx = np.load('/tmp/lat_idx.npy')
lon_idx = np.load('/tmp/lon_idx.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Baseline period with extension
base_start = datetime(1991, 12, 27)
base_end = datetime(2003, 1, 5)

# Generate all dates
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)

n_base = len(base_dates)
print(f"Baseline dates: {n_base}")

# Load all baseline data for region
base_sst = np.zeros((n_base, len(lat_idx), len(lon_idx)), dtype=np.float64)
for i, date in enumerate(base_dates):
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    sst = ds['analysed_sst'].values[0]
    base_sst[i] = sst[np.ix_(lat_idx, lon_idx)].astype(np.float64)
    ds.close()
    if (i+1) % 500 == 0:
        print(f"  Loaded {i+1}/{n_base} days")

print(f"Baseline SST shape: {base_sst.shape}")
np.save('/tmp/base_sst.npy', base_sst)

# Also save the dates
from datetime import datetime as dt
date_strs = [d.strftime('%Y%m%d') for d in base_dates]
np.save('/tmp/base_dates.npy', np.array(date_strs))
print("Saved baseline data")
