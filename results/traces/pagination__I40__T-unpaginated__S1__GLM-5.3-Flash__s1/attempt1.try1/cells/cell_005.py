import fsspec, h5py, numpy as np, datetime as dt, inspect
import numpy.lib._function_base_impl as fb
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 404,463,559,618

# time decoding check
with fs.open(f'{base}/sst_20000301.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        t = hf['time']
        print('time dtype', t.dtype, 'value', t[0], 'units', t.attrs.get('units'), 'cal', t.attrs.get('calendar'))
        print('var keys', list(hf.keys()))

# edge files exist?
for d in ['19911227','19911231','20030101','20030105','19820101','20231231']:
    try:
        with fs.open(f'{base}/sst_{d}.nc','rb') as f:
            print(d, 'ok')
    except Exception as e:
        print(d, 'MISSING', repr(e)[:80])

# seasonal finite pattern in region
for d in ['19920115','19920215','19920315','19920415','19920515','19920615','19921015','19930115','20000115','20090215','20090715']:
    with fs.open(f'{base}/sst_{d}.nc','rb') as f:
        with h5py.File(f,'r') as hf:
            a = hf['analysed_sst'][0, i0:i1+1, j0:j1+1]
    fin = np.isfinite(a)
    print(d, 'finite cells: %d/3600' % fin.sum(), 'sst range', np.nanmin(a), np.nanmax(a))
