
import numpy as np
from datetime import date, timedelta
import xarray as xr
import os

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Load region coordinates
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_idx = np.where((lat_all >= 57.85) & (lat_all <= 59.05))[0]
lon_idx = np.where((lon_all >= 21.01) & (lon_all <= 22.21))[0]
region_lat = lat_all[lat_idx]
region_lon = lon_all[lon_idx]
ds0.close()
nlat, nlon = len(lat_idx), len(lon_idx)

# Baseline dates
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)
n_dates = len(all_dates)
date_to_idx = {d: i for i, d in enumerate(all_dates)}
baseline_1992_2002 = [d for d in all_dates if date(1992,1,1) <= d <= date(2002,12,31)]

# Load baseline SST data
baseline_sst = np.zeros((n_dates, nlat, nlon), dtype=np.float64)
for i, d in enumerate(all_dates):
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    baseline_sst[i] = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    ds.close()

# Build pool dates for each doy
pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool = []
    for D in baseline_1992_2002:
        if doy_of_date(D) == doy:
            for k in range(-5, 6):
                X = D + timedelta(days=k)
                if X in date_to_idx:
                    pool.append(date_to_idx[X])
    pool_dates[doy] = np.array(pool)

# Compute threshold and climatology for each doy (except 60)
threshold = np.full((366, nlat, nlon), np.nan, dtype=np.float64)
climatology = np.full((366, nlat, nlon), np.nan, dtype=np.float64)

for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = pool_dates[doy]
    pool_data = baseline_sst[idxs]
    
    for ilat in range(nlat):
        for ilon in range(nlon):
            vals = pool_data[:, ilat, ilon]
            valid = vals[np.isfinite(vals)]
            if len(valid) > 0:
                threshold[doy-1, ilat, ilon] = np.percentile(valid, 90, method='hazen')
                climatology[doy-1, ilat, ilon] = np.mean(valid)

# Set day 60 (index 59) to mean of days 59 and 61
# Check if days 59 and 61 have values
print("Day 59 (idx 58) NaN count:", np.sum(np.isnan(threshold[58])))
print("Day 61 (idx 60) NaN count:", np.sum(np.isnan(threshold[60])))

# For cells where both 59 and 61 are valid, set day 60 to their mean
valid_59 = np.isfinite(threshold[58])
valid_61 = np.isfinite(threshold[60])
both_valid = valid_59 & valid_61
print("Cells with both 59 and 61 valid:", both_valid.sum())

# Set day 60
threshold[59] = np.where(both_valid, (threshold[58] + threshold[60]) / 2.0, np.nan)
climatology[59] = np.where(both_valid, (climatology[58] + climatology[60]) / 2.0, np.nan)

print("Day 60 threshold sample:", threshold[59, 0, 0])
print("Day 60 climatology sample:", climatology[59, 0, 0])

# Check for any remaining NaN in threshold/climatology
print("NaN count in threshold:", np.sum(np.isnan(threshold)))
print("NaN count in climatology:", np.sum(np.isnan(climatology)))
