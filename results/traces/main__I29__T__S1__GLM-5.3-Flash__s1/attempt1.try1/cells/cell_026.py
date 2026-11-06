import fsspec, h5py, numpy as np, time, datetime
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
i0, i1, j0, j1 = 218, 278, 601, 661
def make_dates(a, b):
    n = (b-a).days+1
    return [a+datetime.timedelta(days=k) for k in range(n)]
def reader(args):
    idx, p, expected = args
    last = None
    for attempt in range(3):
        try:
            f = fs.open(p,'rb')
            with h5py.File(f,'r') as h:
                t = h['time'][:1]
                got = datetime.date(1981,1,1)+datetime.timedelta(seconds=int(t[0]))
                if got != expected: raise ValueError(f'time mismatch {got} != {expected}')
                arr = h['analysed_sst'][0, i0:i1, j0:j1]
            f.close()
            return idx, np.ascontiguousarray(arr, dtype=np.float32), None
        except Exception as e:
            last = e; time.sleep(0.5)
    return idx, None, str(last)
def fetch_chunk(dates, outname):
    paths = [base+'sst_%04d%02d%02d.nc'%(d.year,d.month,d.day) for d in dates]
    tasks = [(i, paths[i], dates[i]) for i in range(len(dates))]
    out = np.full((len(dates),60,60), np.nan, dtype=np.float32)
    errs = []
    t0=time.time()
    with ThreadPoolExecutor(max_workers=32) as ex:
        for idx, arr, err in ex.map(reader, tasks):
            if err is not None: errs.append((idx, dates[idx].isoformat(), err))
            else: out[idx] = arr
    dt = time.time()-t0
    np.save(outname, out)
    print(f'{outname}: {len(dates)} files in {dt:.1f}s, errors: {len(errs)}')
    if errs: print(errs[:5])
    return errs
a = datetime.date(2015,6,1); b = datetime.date(2015,8,31)
errs = fetch_chunk(make_dates(a,b), 'target.npy')
print('done')
