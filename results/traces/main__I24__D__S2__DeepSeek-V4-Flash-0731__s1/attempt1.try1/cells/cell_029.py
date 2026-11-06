
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# First select time, then nearest
sst_point = ds.analysed_sst.sel(time=slice('2004-08-01','2004-08-10'))
sst_point = sst_point.sel(latitude=58.0, longitude=11.0, method='nearest')
print("SST values at nearest to (58.0, 11.0) in Aug 2004:")
print(sst_point.values)

print("\nUnits:", ds.analysed_sst.attrs.get('units', 'not specified'))
print("\nComment:", ds.analysed_sst.attrs.get('comment', 'not specified'))
