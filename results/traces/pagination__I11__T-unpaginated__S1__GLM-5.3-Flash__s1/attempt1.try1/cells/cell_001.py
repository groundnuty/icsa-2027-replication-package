import sys
print(sys.version)
import numpy, xarray, h5netcdf, fsspec
print('numpy', numpy.__version__, '| xarray', xarray.__version__, '| h5netcdf', h5netcdf.__version__, '| fsspec', fsspec.__version__)
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
try:
    entries = fs.ls(p)
except Exception as e:
    print('ERR as given:', repr(e))
    entries = fs.ls('/' + p)
print(type(entries), len(entries))
for e in entries[:50]:
    print(e)
