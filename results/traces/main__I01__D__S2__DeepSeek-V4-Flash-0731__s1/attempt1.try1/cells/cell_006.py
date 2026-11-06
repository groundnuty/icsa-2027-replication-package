
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select region
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]

# Baseline time range
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
t_idx_base = np.where((ds.time.values >= base_start) & (ds.time.values <= base_end))[0]

# Load baseline data
base_sst = ds.analysed_sst.isel(time=t_idx_base, latitude=lat_idx, longitude=lon_idx).values
print("Baseline shape:", base_sst.shape)
print("Baseline dtype:", base_sst.dtype)
print("Baseline NaN count:", np.isnan(base_sst).sum())
print("Baseline range:", np.nanmin(base_sst), np.nanmax(base_sst))

# Target time range
tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((ds.time.values >= tgt_start) & (ds.time.values <= tgt_end))[0]
tgt_sst = ds.analysed_sst.isel(time=t_idx_tgt, latitude=lat_idx, longitude=lon_idx).values
print("Target shape:", tgt_sst.shape)
print("Target NaN count:", np.isnan(tgt_sst).sum())
print("Target range:", np.nanmin(tgt_sst), np.nanmax(tgt_sst))
