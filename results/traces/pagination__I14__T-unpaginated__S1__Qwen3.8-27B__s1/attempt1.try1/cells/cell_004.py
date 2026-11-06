
import importlib
for m in ['xarray','numpy','netCDF4','h5netcdf','fsspec']:
    try:
        mod = importlib.import_module(m)
        print(m, getattr(mod,'__version__','?'))
    except Exception as e:
        print(m, 'ERR', e)
