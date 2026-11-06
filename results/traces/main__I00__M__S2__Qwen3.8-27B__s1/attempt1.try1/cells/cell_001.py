import sys
print(sys.version)
import numpy, xarray, netCDF4
print("numpy", numpy.__version__)
print("xarray", xarray.__version__)
print("netCDF4", netCDF4.__version__)
try:
    import h5netcdf
    print("h5netcdf", h5netcdf.__version__)
except Exception as e:
    print("h5netcdf missing:", e)

ds = xarray.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
print(ds)
print("---- attrs ----")
for k,v in ds.attrs.items():
    print(k, "=", str(v)[:200])
