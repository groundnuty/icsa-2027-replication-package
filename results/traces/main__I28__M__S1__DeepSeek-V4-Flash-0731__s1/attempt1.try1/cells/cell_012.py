
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

# Region indices
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_mask = (lat_all >= 57.85) & (lat_all <= 59.05)
lon_mask = (lon_all >= 21.01) & (lon_all <= 22.21)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
ds0.close()

# Baseline extended range
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)

# Load baseline data for the region
baseline_dates = []
baseline_sst = []
d = base_start
while d <= base_end:
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    sst_region = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    baseline_sst.append(sst_region.astype(np.float64))
    baseline_dates.append(d)
    ds.close()
    d += timedelta(days=1)

baseline_sst = np.array(baseline_sst)
print(f"Baseline data shape: {baseline_sst.shape}")
print(f"Baseline dates: {baseline_dates[0]} to {baseline_dates[-1]}, count: {len(baseline_dates)}")
print(f"Memory: {baseline_sst.nbytes / 1e6:.1f} MB")
