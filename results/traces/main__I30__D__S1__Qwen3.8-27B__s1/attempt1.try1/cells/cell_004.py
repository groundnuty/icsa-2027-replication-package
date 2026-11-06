import os, time, fsspec
from concurrent.futures import ThreadPoolExecutor, as_completed
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
from datetime import date, timedelta
def drange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)
all_dates = sorted(set(
    [date(1991,12,27)+timedelta(i) for i in range(5)] +
    list(drange(date(1992,1,1), date(2002,12,31))) +
    [date(2003,1,1)+timedelta(i) for i in range(5)] +
    list(drange(date(2010,6,1), date(2010,8,31)))
))
names = ['sst_%s.nc' % d.strftime('%Y%m%d') for d in all_dates]

missing, failed = [], []
def one(nm, attempt=0):
    local = '/work/data/' + nm
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return 'ok'
    try:
        fs.get(base + '/' + nm, local)
        return 'ok'
    except Exception as e:
        if attempt < 3:
            time.sleep(1 + attempt)
            return one(nm, attempt+1)
        return ('missing', str(e))

t0 = time.time()
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = {ex.submit(one, nm): nm for nm in names}
    done = 0
    for f in as_completed(futs):
        r = f.result()
        done += 1
        if isinstance(r, tuple):
            failed.append((futs[f], r[1][:120]))
        if done % 500 == 0:
            print(done, "done, %.0fs" % (time.time()-t0))
print("total done:", done, "in %.0fs" % (time.time()-t0))
print("failed:", len(failed))
for x in failed[:10]: print(x)
# verify all present
absent = [n for n in names if not (os.path.exists('/work/data/'+n) and os.path.getsize('/work/data/'+n) > 0)]
print("absent:", len(absent), absent[:10])
