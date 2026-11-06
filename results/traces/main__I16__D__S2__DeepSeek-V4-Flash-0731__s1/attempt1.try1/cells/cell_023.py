
import numpy as np
import xarray as xr

threshold_smooth = np.load('/work/threshold_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_idx = np.where((lon >= 20.23) & (lon <= 21.43))[0]
time = ds.time.values
t_start = np.where(time >= np.datetime64('2008-06-01'))[0][0]
t_end = np.where(time <= np.datetime64('2008-08-31'))[0][-1]
target_region = ds['analysed_sst'].isel(time=slice(t_start, t_end+1),
                                        latitude=lat_idx, longitude=lon_idx).load()
target_data = target_region.values.astype(np.float64)
sea_mask = np.all(np.isfinite(target_data), axis=0)  # (60, 60)

# Check sea cells NaN in smoothed threshold
nan_in_sea = np.any(np.isnan(threshold_smooth[:, sea_mask]), axis=0)  # (60,60) but sea_mask is (60,60)
# This indexes along last two axes
print("Sea cells with NaN in smoothed threshold:", np.sum(nan_in_sea))
