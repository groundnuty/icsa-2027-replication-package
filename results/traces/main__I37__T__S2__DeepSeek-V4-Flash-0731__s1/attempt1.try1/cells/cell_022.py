
import pandas as pd
import numpy as np
import fsspec
import xarray as xr

fs = fsspec.filesystem('onedata')
data_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21

def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

with fs.open(data_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values
    lon = ds.longitude.values
    time_vals = ds.time.values
    all_dates = pd.to_datetime(time_vals)
    
    lat_idx = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_idx = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    
    ext_start = pd.Timestamp('1991-12-27')
    ext_end = pd.Timestamp('2003-01-05')
    ext_time_idx = np.where((all_dates >= ext_start) & (all_dates <= ext_end))[0]
    
    tgt_start = pd.Timestamp('2012-06-01')
    tgt_end = pd.Timestamp('2012-08-31')
    tgt_time_idx = np.where((all_dates >= tgt_start) & (all_dates <= tgt_end))[0]
    
    baseline_sst = ds['analysed_sst'].isel(
        time=slice(int(ext_time_idx[0]), int(ext_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)
    
    target_sst = ds['analysed_sst'].isel(
        time=slice(int(tgt_time_idx[0]), int(tgt_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)

# Check target SST values and thresholds for a few cells
print("Target SST range:", np.nanmin(target_sst), "to", np.nanmax(target_sst))

# Check baseline SST range
print("Baseline SST range:", np.nanmin(baseline_sst), "to", np.nanmax(baseline_sst))

# For a specific sea cell, check its values
# Let's find a sea cell
sea_cells = ~np.isnan(target_sst).any(axis=0)
sea_idx = np.where(sea_cells)
print(f"First sea cell: ({sea_idx[0][0]}, {sea_idx[1][0]})")

i, j = sea_idx[0][0], sea_idx[1][0]
print(f"\nTarget SST for cell ({i},{j}):")
print(target_sst[:, i, j])

# Check baseline values for this cell
print(f"\nBaseline SST for cell ({i},{j}) around June-August:")
# Find baseline dates in Jun-Aug
ext_dates_pd = pd.date_range('1991-12-27', '2003-01-05', freq='D')
for year in [1992, 1995, 2000]:
    mask = (ext_dates_pd >= pd.Timestamp(f'{year}-06-01')) & (ext_dates_pd <= pd.Timestamp(f'{year}-08-31'))
    idxs = np.where(mask)[0]
    vals = baseline_sst[idxs, i, j]
    print(f"  {year}: {vals[:5]}... mean={np.nanmean(vals):.2f}, max={np.nanmax(vals):.2f}")
