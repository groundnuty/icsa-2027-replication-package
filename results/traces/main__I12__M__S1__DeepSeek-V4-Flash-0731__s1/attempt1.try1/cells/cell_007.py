
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
sst = ds.analysed_sst.values[0]  # (lat, lon)
print("Shape:", sst.shape)
print("dtype:", sst.dtype)

# Region indices
lat_idx = slice(130, 190)  # 130 to 189 inclusive
lon_idx = slice(78, 138)   # 78 to 137 inclusive
region = sst[lat_idx, lon_idx]
print("Region shape:", region.shape)
print("Region min:", np.nanmin(region), "max:", np.nanmax(region))
print("NaN count:", np.isnan(region).sum())
print("Non-NaN count:", np.sum(~np.isnan(region)))
print("Sample values:")
print(region[:5, :5])
