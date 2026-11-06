
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

# Load baseline data (1991-12-27 to 2003-01-05)
baseline_data = ds.analysed_sst.sel(
    time=slice('1991-12-27', '2003-01-05'),
    latitude=ds.latitude.values[lat_idx],
    longitude=ds.longitude.values[lon_idx]
).load()

print("Baseline data shape:", baseline_data.shape)
print("Baseline time range:", baseline_data.time.values[0], baseline_data.time.values[-1])
