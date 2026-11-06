
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Region indices
lat_idx = slice(330, 390)  # 330 to 389
lon_idx = slice(551, 611)  # 551 to 610

# Load extended baseline data (1991-12-27 to 2003-01-05)
ext_start_idx = 3647
ext_end_idx = 7675  # inclusive

# Let's check the actual times at those indices
times = ds.time.values
print("Ext baseline time range:", times[ext_start_idx], "to", times[ext_end_idx-1])

# Read the data
data = ds['analysed_sst'].isel(time=slice(ext_start_idx, ext_end_idx), 
                                latitude=lat_idx, longitude=lon_idx).values
print("Data shape:", data.shape)
print("Data dtype:", data.dtype)
print("NaN count:", np.isnan(data).sum())
print("Finite count:", np.isfinite(data).sum())
print("Min:", np.nanmin(data), "Max:", np.nanmax(data))
