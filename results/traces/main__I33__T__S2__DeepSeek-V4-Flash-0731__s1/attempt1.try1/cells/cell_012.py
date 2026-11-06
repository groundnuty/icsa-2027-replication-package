
import fsspec
import xarray as xr
import numpy as np
import pickle

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Region indices
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
lat_idx = np.where((ds.latitude.values >= lat_min) & (ds.latitude.values <= lat_max))[0]
lon_idx = np.where((ds.longitude.values >= lon_min) & (ds.longitude.values <= lon_max))[0]
lat_vals = ds.latitude.values[lat_idx]
lon_vals = ds.longitude.values[lon_idx]

# Load baseline data (1991-12-27 to 2003-01-05)
baseline_data = ds.analysed_sst.sel(
    time=slice('1991-12-27', '2003-01-05'),
    latitude=lat_vals,
    longitude=lon_vals
).load()

# Load target data (2014-06-01 to 2014-08-31)
target_data = ds.analysed_sst.sel(
    time=slice('2014-06-01', '2014-08-31'),
    latitude=lat_vals,
    longitude=lon_vals
).load()

print("Baseline shape:", baseline_data.shape)
print("Target shape:", target_data.shape)
print("Baseline NaN count:", np.isnan(baseline_data.values).sum())
print("Target NaN count:", np.isnan(target_data.values).sum())

# Save to files for later use
baseline_data.to_netcdf('baseline_data.nc')
target_data.to_netcdf('target_data.nc')
print("Saved.")
