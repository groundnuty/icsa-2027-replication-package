
import importlib
for m in ['xarray','netCDF4','h5netcdf','numpy','scipy','pandas','dask']:
    try:
        mod = importlib.import_module(m)
        print(m, getattr(mod,'__version__','?'))
    except Exception as e:
        print(m, 'MISSING')
