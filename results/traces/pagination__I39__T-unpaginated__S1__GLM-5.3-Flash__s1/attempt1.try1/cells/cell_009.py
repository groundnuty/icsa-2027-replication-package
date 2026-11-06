import fsspec, h5py, numpy as np, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
BASE='icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 350,409,413,472

def read_one(dstr):
    with fs.open(f'{BASE}/sst_{dstr}.nc','rb') as f:
        with h5py.File(f,'r') as h:
            a = h['analysed_sst'][0, i0:i1+1, j0:j1+1]
            t = int(h['time'][0])
    return dstr, t, np.asarray(a, dtype=np.float32)

dstrs = [(dt.date(2010,6,1)+dt.timedelta(days=k)).strftime('%Y%m%d') for k in range(60)]
with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(read_one, dstrs))
ok=True
for dstr, t, a in res:
    d = dt.datetime.strptime(dstr,'%Y%m%d').date()
    expect = (d - dt.date(1981,1,1)).days*86400
    if t != expect: print('TIME MISMATCH', dstr, t, expect); ok=False
    if a.shape != (60,60): print('SHAPE', dstr, a.shape); ok=False
print('time/shape consistent:', ok)

# Check nan patterns stable across a few files (land mask) & day-to-day variability
for k in [0,1,2,45,59]:
    dstr,t,a = res[k]
    print(dstr, 'nan%', round(float(np.isnan(a).mean()),4), 'mean', round(float(np.nanmean(a)),2), 'min', float(np.nanmin(a)), 'max', float(np.nanmax(a)))

# how many region cells are NaN-free on this first day?
print('cells non-nan day1:', int((~np.isnan(res[0][2])).sum()), 'of', 60*60)
