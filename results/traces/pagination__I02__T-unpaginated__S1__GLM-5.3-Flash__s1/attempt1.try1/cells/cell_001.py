import fsspec, numpy, xarray, sys
fs = fsspec.filesystem('onedata')
items = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
print("n_items:", len(items))
for it in items[:60]:
    print(it.get('type'), it.get('name'), it.get('size'))
print("numpy", numpy.__version__, "xarray", xarray.__version__)
try:
    import h5netcdf; print("h5netcdf", h5netcdf.__version__)
except Exception as e:
    print("h5netcdf missing:", e)
try:
    import netCDF4; print("netCDF4", netCDF4.__version__)
except Exception as e:
    print("netCDF4 missing:", e)
