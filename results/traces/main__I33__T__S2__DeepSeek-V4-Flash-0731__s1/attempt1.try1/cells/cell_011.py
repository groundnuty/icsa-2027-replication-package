
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Region indices
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
lat_idx = np.where((ds.latitude.values >= lat_min) & (ds.latitude.values <= lat_max))[0]
lon_idx = np.where((ds.longitude.values >= lon_min) & (ds.longitude.values <= lon_max))[0]

# Load target data (2014-06-01 to 2014-08-31)
target_data = ds.analysed_sst.sel(
    time=slice('2014-06-01', '2014-08-31'),
    latitude=ds.latitude.values[lat_idx],
    longitude=ds.longitude.values[lon_idx]
).load()

print("Target data shape:", target_data.shape)
print("Target time range:", target_data.time.values[0], target_data.time.values[-1])

# Save for later use
import pickle
with open('data_region.pkl', 'wb') as fout:
    # Can't pickle xarray easily with fsspec, let's just use numpy
    pass

# Let's check if there's NaN in baseline and target
print("Baseline NaN count:", np.isnan(baseline_data.values).sum())
print("Target NaN count:", np.isnan(target_data.values).sum())
