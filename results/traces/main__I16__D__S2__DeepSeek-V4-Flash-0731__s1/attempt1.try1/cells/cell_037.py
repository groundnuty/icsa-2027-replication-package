
import numpy as np
import xarray as xr

# Verify the mhw_mask and events
mhw_mask = np.load('/work/mhw_mask.npy')
print("mhw_mask shape:", mhw_mask.shape)
print("mhw_mask dtype:", mhw_mask.dtype)

# Active days
active = np.any(mhw_mask, axis=(1, 2))
print("Active day indices:", np.where(active)[0])

# Check target period dates
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
t_start = np.where(time >= np.datetime64('2008-06-01'))[0][0]
t_end = np.where(time <= np.datetime64('2008-08-31'))[0][-1]
target_times = time[t_start:t_end+1]
print("Target times:", target_times[0], "to", target_times[-1])
print("N target:", len(target_times))

# Regional event dates
for idx in np.where(active)[0]:
    print(f"Day {idx}: {str(target_times[idx])[:10]}")
