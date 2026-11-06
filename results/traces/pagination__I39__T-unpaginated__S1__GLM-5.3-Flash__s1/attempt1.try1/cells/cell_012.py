import fsspec, h5py, numpy as np, datetime as dt, time, os, json
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
BASE = 'icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 350,409,413,472

# date lists
def daterange(a,b):
    out=[]; cur=a
    while cur<=b:
        out.append(cur); cur+=dt.timedelta(days=1)
    return out
base_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates  = daterange(dt.date(2010,6,1), dt.date(2010,8,31))
all_dates = base_dates + tgt_dates
print('baseline ext days', len(base_dates), 'target days', len(tgt_dates), 'total', len(all_dates))

EPOCH = dt.date(1981,1,1)
def read_one(d):
    dstr = d.strftime('%Y%m%d')
    last_err = None
    for attempt in range(4):
        try:
            with fs.open(f'{BASE}/sst_{dstr}.nc','rb') as f:
                with h5py.File(f,'r') as h:
                    a = h['analysed_sst'][0, i0:i1+1, j0:j1+1]
                    t = int(h['time'][0])
            return dstr, t, np.asarray(a, dtype=np.float32)
        except Exception as e:
            last_err = e
            time.sleep(1.0+attempt)
    return dstr, None, last_err

t0=time.time()
with ThreadPoolExecutor(16) as ex:
    results = list(ex.map(read_one, all_dates))
el = time.time()-t0
print(f'read {len(results)} files in {el:.1f}s ({len(results)/el:.1f} files/s)')

fails = [r for r in results if r[1] is None]
print('failures:', len(fails), [r[0] for r in fails][:10])

# assemble
ok = [r for r in results if r[1] is not None]
ok.sort(key=lambda r: r[0])
S = np.full((len(all_dates), 60, 60), np.nan, dtype=np.float32)
date_index = {d.strftime('%Y%m%d'): k for k,d in enumerate(all_dates)}
time_ok = True
for dstr, t, a in ok:
    d = dt.datetime.strptime(dstr,'%Y%m%d').date()
    if t != (d-EPOCH).days*86400:
        print('TIME MISMATCH', dstr, t); time_ok=False
    S[date_index[dstr]] = a
print('time stamps all consistent:', time_ok)
print('filled', len(ok), 'of', len(all_dates))

os.makedirs('/tmp/mhw', exist_ok=True)
np.save('/tmp/mhw/S32.npy', S)
np.save('/tmp/mhw/dates.npy', np.array([d.strftime('%Y-%m-%d') for d in all_dates]))
print('saved S32.npy shape', S.shape, 'dtype', S.dtype)
print('overall nan frac', float(np.isnan(S).mean()))
