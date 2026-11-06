
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds['analysed_sst'].attrs)
print(ds['analysed_sst'].units if hasattr(ds['analysed_sst'], 'units') else "No units attribute")
print(ds.attrs)
