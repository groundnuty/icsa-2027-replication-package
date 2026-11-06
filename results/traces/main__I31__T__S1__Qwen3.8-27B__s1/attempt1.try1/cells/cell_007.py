
import importlib, sys
print(sys.version)
for m in ['xarray','numpy','h5netcdf','netCDF4','scipy','pandas','fsspec','numba','dask']:
    try:
        mod = importlib.import_module(m)
        print(m, getattr(mod,'__version__','?'))
    except Exception as e:
        print(m, 'MISSING', type(e).__name__)
