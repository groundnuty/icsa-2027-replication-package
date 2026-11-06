
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds.analysed_sst.attrs)
print(ds.analysed_sst.encoding)
# Check some values
v = ds.analysed_sst.isel(time=0, latitude=550, longitude=730).values
print("Sample value:", v)
