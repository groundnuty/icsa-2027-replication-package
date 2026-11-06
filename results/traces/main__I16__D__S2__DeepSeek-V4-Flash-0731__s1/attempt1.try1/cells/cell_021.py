
import xarray as xr
import numpy as np

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

# Sea cells: finite on every day of target period
target_data = target_region.values.astype(np.float64)
finite_all = np.all(np.isfinite(target_data), axis=0)
print("Sea cells:", np.sum(finite_all), "out of", lat_idx.size * lon_idx.size)

# Check: do sea cells have complete baseline data?
# Load baseline data
b_start = np.where(time >= np.datetime64('1991-12-27'))[0][0]
b_end = np.where(time <= np.datetime64('2003-01-05'))[0][-1]
baseline_region = ds['analysed_sst'].isel(time=slice(b_start, b_end+1), 
                                          latitude=lat_idx, longitude=lon_idx).load()
baseline_data = baseline_region.values.astype(np.float64)

# For sea cells, check how many baseline days are NaN
sea_mask = finite_all
nan_count_per_sea_cell = np.sum(~np.isfinite(baseline_data[:, sea_mask]), axis=0)
print("NaN days in baseline for sea cells: min={}, max={}".format(
    np.min(nan_count_per_sea_cell), np.max(nan_count_per_sea_cell)))
