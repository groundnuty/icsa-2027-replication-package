
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

times = ds.time.values
lat_s, lat_e = 66, 125
lon_s, lon_e = 531, 590

# Read baseline data
print("Reading baseline data...")
base_data = ds['analysed_sst'].isel(
    time=slice(3647, 7675),
    latitude=slice(lat_s, lat_e+1),
    longitude=slice(lon_s, lon_e+1)
).values
print("Baseline data shape:", base_data.shape)

# Read target data
print("Reading target data...")
target_data = ds['analysed_sst'].isel(
    time=slice(9282, 9374),
    latitude=slice(lat_s, lat_e+1),
    longitude=slice(lon_s, lon_e+1)
).values
print("Target data shape:", target_data.shape)

# Get time values
base_times = times[3647:7675]
tgt_times = times[9282:9374]

# Save data for later
np.save('/tmp/base_data.npy', base_data)
np.save('/tmp/target_data.npy', target_data)
np.save('/tmp/base_times.npy', base_times)
np.save('/tmp/tgt_times.npy', tgt_times)
np.save('/tmp/lat_vals.npy', ds.latitude.values[lat_s:lat_e+1])
np.save('/tmp/lon_vals.npy', ds.longitude.values[lon_s:lon_e+1])
print("Saved.")
print("Base times:", base_times[0], base_times[-1])
print("Tgt times:", tgt_times[0], tgt_times[-1])
