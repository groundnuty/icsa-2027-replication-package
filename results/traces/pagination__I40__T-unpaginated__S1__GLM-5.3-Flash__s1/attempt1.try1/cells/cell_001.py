import sys
print(sys.version)
import numpy as np, xarray as xr
print('numpy', np.__version__, 'xarray', xr.__version__)
for mod in ['h5netcdf','netCDF4','h5py']:
    try:
        m = __import__(mod); print(mod, getattr(m,'__version__','?'))
    except Exception as e:
        print('no', mod, repr(e)[:100])

import fsspec
fs = fsspec.filesystem('onedata')
base = None; ent = None
for p in ['icsa2027_data_20261101T090944Z/s1z', '/icsa2027_data_20261101T090944Z/s1z']:
    try:
        ent = fs.ls(p); base = p; break
    except Exception as e:
        print('fail', p, repr(e)[:200])
print('base =', base)
def nm(e):
    return e.get('name') if isinstance(e, dict) else e
names = [nm(e) for e in ent]
print('n entries', len(names))
for n in names[:8]: print(n)
print('...')
for n in names[-4:]: print(n)
