
import xarray as xr
import numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_sel = (ds.latitude.values >= 54.45) & (ds.latitude.values <= 55.65)
lon_sel = (ds.longitude.values >= 16.05) & (ds.longitude.values <= 17.25)

# Get region data
sst_region = ds.analysed_sst[:, lat_sel, lon_sel]
print("Region shape:", sst_region.shape)

# Get times
t = ds.time.values

# Load baseline data
start_baseline = np.datetime64('1991-12-27')
end_baseline = np.datetime64('2003-01-05')
mask_baseline = (t >= start_baseline) & (t <= end_baseline)
baseline_idx = np.where(mask_baseline)[0]

sst_baseline = sst_region[baseline_idx, :, :].values
print("Baseline SST shape:", sst_baseline.shape)
print("Baseline NaN count:", np.isnan(sst_baseline).sum())

# Target data
start_target = np.datetime64('2012-06-01')
end_target = np.datetime64('2012-08-31')
mask_target = (t >= start_target) & (t <= end_target)
target_idx = np.where(mask_target)[0]

sst_target = sst_region[target_idx, :, :].values
print("Target SST shape:", sst_target.shape)
print("Target NaN count:", np.isnan(sst_target).sum())
