import fsspec, h5py, numpy as np, time, datetime as dt
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
import numpy, scipy, xarray
print('numpy', numpy.__version__, '| scipy', scipy.__version__, '| xarray', xarray.__version__)

with fs.open(f'{base}/sst_20220601.nc','rb') as f:
    with h5py.File(f,'r') as h:
        d = h['analysed_sst']
        print('chunks:', d.chunks, 'compression:', d.compression, 'shape:', d.shape)
        print('time raw:', h['time'][:], h['time'].attrs)

# verify filename date == dataset time via xarray on 2 files
import xarray as xr
for dstr in ['19911227','20030105']:
    with fs.open(f'{base}/sst_{dstr}.nc','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print(dstr, '->', ds.time.values, ds.latitude.encoding.get('dtype'), ds.analysed_sst.dtype)

# benchmark 128 files with 48 threads
i0,i1,j0,j1 = 66,125,531,590
d0 = dt.date(2022,6,1)
dates = [(d0+dt.timedelta(days=k)).strftime('%Y%m%d') for k in range(128)]
def read_region(dstr):
    for attempt in range(3):
        try:
            with fs.open(f'{base}/sst_{dstr}.nc','rb') as f:
                with h5py.File(f,'r') as h:
                    return dstr, h['analysed_sst'][0, i0:i1+1, j0:j1+1].astype(np.float64)
        except Exception as e:
            if attempt==2: raise
            time.sleep(1)
import concurrent.futures as cf
t0=time.time()
with cf.ThreadPoolExecutor(48) as ex:
    res = dict(ex.map(read_region, dates))
el=time.time()-t0
print(f'128 files in {el:.1f}s -> {128/el:.1f} files/s; est 4120 files: {4120*el/128:.0f}s')
print('finite frac mean:', np.mean([np.isfinite(v).mean() for v in res.values()]))
