import sys, os, shutil
print(sys.version)
import numpy as np
print('numpy', np.__version__)
for m in ['netCDF4','h5netcdf','h5py','xarray','fsspec','pandas']:
    try:
        mod = __import__(m); print(m, getattr(mod,'__version__','?'))
    except Exception as e:
        print(m, 'MISSING', type(e).__name__)
try:
    print('cwd:', os.getcwd())
    print('disk /work:', shutil.disk_usage('/work'))
except Exception as e:
    print('disk err', e)
# quick check of hazen quantile support
try:
    print('hazen q:', np.quantile(np.array([1.,2,3,4]), 0.9, method='hazen'))
except Exception as e:
    print('hazen method missing:', e)
import fsspec
fs = fsspec.filesystem('onedata')
for p in ['/', 'icsa2027_data_20261101T090944Z', 'icsa2027_data_20261101T090944Z/s1z']:
    try:
        ls = fs.ls(p)
        if isinstance(ls, list):
            print('LS', repr(p), 'n=', len(ls))
            for x in ls[:15]:
                print('   ', x)
        else:
            print('LS', repr(p), ls)
    except Exception as e:
        print('LS', repr(p), 'ERR', type(e).__name__, str(e)[:200])
