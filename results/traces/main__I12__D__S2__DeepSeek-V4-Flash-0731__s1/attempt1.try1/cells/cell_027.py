
import numpy as np
import pandas as pd
import xarray as xr

# Reload and check the hot day pattern for cell (54, 20)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]
mask_t = (time >= pd.Timestamp('2009-06-01')) & (time <= pd.Timestamp('2009-08-31'))
idx_target = np.where(mask_t)[0]

base_time = time[idx_base]
target_time = time[idx_target]
base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Check the hot day pattern for cell (54, 20)
i, j = 54, 20

# I need to recompute the threshold for this cell. Let me use the already-computed values from the mask.
# Actually, let me just load the mask and check the MHW pattern, then recompute the hot days.

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values

print(f"Cell ({i},{j}): lat={lat[lat_idx[i]]:.2f}, lon={lon[lon_idx[j]]:.2f}")
print(f"MHW pattern (first 40 days):")
for t in range(40):
    date_str = pd.Timestamp(ds_out.time.values[t]).strftime('%Y-%m-%d')
    in_mhw = mhw[t, i, j]
    if in_mhw:
        print(f"  {date_str}: in MHW")
