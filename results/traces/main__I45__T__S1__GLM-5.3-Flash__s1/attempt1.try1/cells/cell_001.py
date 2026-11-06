import sys, numpy as np
print('py', sys.version.split()[0], 'np', np.__version__)
import xarray as xr; print('xr', xr.__version__)
for m in ['h5netcdf','netCDF4','h5py','fsspec','scipy']:
    try:
        mod=__import__(m); print(m, getattr(mod,'__version__','?'))
    except Exception as e: print(m,'MISSING',type(e).__name__)

import fsspec
fs = fsspec.filesystem('onedata')
cands = ['icsa2027_data_20261101T090944Z/s1z','/icsa2027_data_20261101T090944Z/s1z']
for p in cands:
    try:
        ls = fs.ls(p, detail=False); print('OK',p,'n',len(ls))
        det = fs.ls(p, detail=True)
        tot = sum(d.get('size',0) for d in det if d.get('type')=='file')
        print('total bytes', tot)
        for d in det[:25]: print('  ', d.get('type'), d.get('name'), d.get('size'))
        if len(det)>25: print('   ... +', len(det)-25)
        break
    except Exception as e:
        print('FAIL',p,type(e).__name__,str(e)[:200])
