
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_idx = list(range(34, 94))
lon_idx = list(range(213, 273))

time = ds['time'].values
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]

target_sst = ds['analysed_sst'].isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values

# Sea cells: cells with finite SST on every day of target period
sea_cells = ~np.isnan(target_sst).any(axis=0)
print("Sea cells count:", sea_cells.sum(), "of", sea_cells.size)
print("Sea cell indices (lat, lon):")
sea_idx = np.where(sea_cells)
print("lat index range:", sea_idx[0].min(), sea_idx[0].max())
print("lon index range:", sea_idx[1].min(), sea_idx[1].max())
print("Number of sea cells:", len(sea_idx[0]))
