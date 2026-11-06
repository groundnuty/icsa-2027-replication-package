
import xarray as xr
import numpy as np

# Check a file's data in the region
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040101.nc', engine='h5netcdf')
data = ds['analysed_sst'].values
# Region indices: lat 34-93, lon 213-272
region_data = data[0, 34:94, 213:273]
print("Region shape:", region_data.shape)
print("NaN count:", np.isnan(region_data).sum())
print("Finite count:", np.isfinite(region_data).sum())
print("Total cells:", region_data.size)
print("Min:", np.nanmin(region_data), "Max:", np.nanmax(region_data))
print("First few values:")
print(region_data[:5, :5])
