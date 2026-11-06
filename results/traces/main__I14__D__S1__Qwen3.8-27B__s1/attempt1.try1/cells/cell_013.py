import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
day = v.isel(time=365).values  # 1983-01-01 (365 days after 1982-01-01)
print("1983-01-01 read ok:", day.shape, day.dtype)
a = xr.open_dataset('/work/data/sst_19830101.nc', engine="h5netcdf")['analysed_sst'].values[0]
print("identical (incl NaN):", np.array_equal(a, day, equal_nan=True))