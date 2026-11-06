import sys
print(sys.version)
import numpy as np
print('numpy', np.__version__)
for mod in ['xarray','h5netcdf','netCDF4','scipy','pandas']:
    try:
        m = __import__(mod); print(mod, getattr(m,'__version__','?'))
    except Exception as e:
        print(mod, 'ERR', repr(e))

import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
try:
    ls = fs.ls(base, detail=True)
    print('n entries:', len(ls))
    for e in ls[:100]:
        print(e.get('type'), e.get('name'), e.get('size'))
    if len(ls) > 100:
        print('... and', len(ls)-100, 'more')
        for e in ls[-5:]:
            print(e.get('type'), e.get('name'), e.get('size'))
except Exception as e:
    print('ls ERR', repr(e))
