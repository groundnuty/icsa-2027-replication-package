
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Get time values
times = ds.time.values
lat_s, lat_e = 66, 125
lon_s, lon_e = 531, 590

# Read target data
print("Reading target data...")
target_data = ds['analysed_sst'].isel(
    time=slice(9282, 9374),
    latitude=slice(lat_s, lat_e+1),
    longitude=slice(lon_s, lon_e+1)
).values
print("Target data shape:", target_data.shape)
print("Target data range:", np.nanmin(target_data), np.nanmax(target_data))

# Get the time values for baseline and target
base_times = times[3647:7675]
tgt_times = times[9282:9374]
print("Baseline times:", base_times[0], "to", base_times[-1])
print("Target times:", tgt_times[0], "to", tgt_times[-1])

# Save the data for later processing
np.save('/tmp/base_data.npy', base_data)
np.save('/tmp/target_data.npy', target_data)
np.save('/tmp/base_times.npy', base_times)
np.save('/tmp/tgt_times.npy', tgt_times)
np.save('/tmp/lat_vals.npy', ds.latitude.values[lat_s:lat_e+1])
np.save('/tmp/lon_vals.npy', ds.longitude.values[lon_s:lon_e+1])
print("Saved.")
