
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
baseline_sel = region.sel(time=slice('1991-12-27', '2003-01-05'))
target_sel = region.sel(time=slice('2004-06-01', '2004-08-31'))

# Load to memory
baseline_sst = baseline_sel.analysed_sst.values.astype(np.float64)  # (4028, 60, 60)
target_sst = target_sel.analysed_sst.values.astype(np.float64)      # (92, 60, 60)
baseline_time = baseline_sel.time.values
target_time = target_sel.time.values

print("baseline_sst shape", baseline_sst.shape)
print("target_sst shape", target_sst.shape)
print("baseline_time", baseline_time[0], baseline_time[-1])
print("target_time", target_time[0], target_time[-1])

# Save to disk for later reuse
np.save('/work/baseline_sst.npy', baseline_sst)
np.save('/work/target_sst.npy', target_sst)
np.save('/work/baseline_time.npy', baseline_time)
np.save('/work/target_time.npy', target_time)
print("saved")
