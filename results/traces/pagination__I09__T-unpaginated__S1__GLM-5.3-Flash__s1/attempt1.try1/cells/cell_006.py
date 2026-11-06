import fsspec, h5py, numpy as np, time, datetime as dt, concurrent.futures as cf
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 66,125,531,590
d0 = dt.date(2022,1,1)
dates = [(d0+dt.timedelta(days=k)).strftime('%Y%m%d') for k in range(256)]
def read_region(dstr):
    for attempt in range(4):
        try:
            with fs.open(f'{base}/sst_{dstr}.nc','rb') as f:
                with h5py.File(f,'r') as h:
                    return dstr, h['analysed_sst'][0, i0:i1+1, j0:j1+1].astype(np.float64)
        except Exception:
            if attempt==3: raise
            time.sleep(0.5+attempt)
for nt in [96, 192]:
    t0=time.time()
    with cf.ThreadPoolExecutor(nt) as ex:
        res = dict(ex.map(read_region, dates))
    el=time.time()-t0
    print(f'{nt} threads: 256 files in {el:.1f}s -> {256/el:.1f} files/s; est 4212 files: {4212*el/256:.0f}s')
