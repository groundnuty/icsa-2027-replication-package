
import xarray as xr
import numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

t = ds.time.values
start_target = np.datetime64('2012-06-01')
end_target = np.datetime64('2012-08-31')
mask_target = (t >= start_target) & (t <= end_target)
target_idx = np.where(mask_target)[0]

lat_sel = (ds.latitude.values >= 54.45) & (ds.latitude.values <= 55.65)
lon_sel = (ds.longitude.values >= 16.05) & (ds.longitude.values <= 17.25)

sst_target = ds.analysed_sst[target_idx, :, :].values
sst_target = sst_target[:, lat_sel, :]
sst_target = sst_target[:, :, lon_sel]
print("Target SST shape:", sst_target.shape)

sea_cells = ~np.isnan(sst_target).any(axis=0)
print("Sea cells:", sea_cells.sum(), "out of", sea_cells.size)
print("Per lat:", sea_cells.sum(axis=1))
print("Per lon:", sea_cells.sum(axis=0))
