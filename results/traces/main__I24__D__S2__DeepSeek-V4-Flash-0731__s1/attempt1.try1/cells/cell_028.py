
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Check SST values near the region
sst_point = ds.analysed_sst.sel(latitude=58.0, longitude=11.0, method='nearest', time=slice('2004-08-01','2004-08-10'))
print("SST values at (58.0, 11.0) in Aug 2004:")
print(sst_point.values)

print("\nUnits:", ds.analysed_sst.attrs.get('units', 'not specified'))
print("\nComment:", ds.analysed_sst.attrs.get('comment', 'not specified'))
