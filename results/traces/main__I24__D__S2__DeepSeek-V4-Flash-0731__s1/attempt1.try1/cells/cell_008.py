
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

# Select region
region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Select baseline period with window extension
baseline_sel = region.sel(time=slice('1991-12-27', '2003-01-05'))
target_sel = region.sel(time=slice('2004-06-01', '2004-08-31'))

print(baseline_sel.analysed_sst.shape)
print(target_sel.analysed_sst.shape)
print(baseline_sel.time.values[0], baseline_sel.time.values[-1])
print(target_sel.time.values[0], target_sel.time.values[-1])
