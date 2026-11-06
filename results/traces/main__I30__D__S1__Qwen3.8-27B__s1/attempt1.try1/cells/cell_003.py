import os, shutil, time, fsspec
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
print(shutil.disk_usage('/work'))

# build date lists
from datetime import date, timedelta
def drange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)

pre = [date(1991,12,27)+timedelta(i) for i in range(5)]
base_days = list(drange(date(1992,1,1), date(2002,12,31)))
post = [date(2003,1,1)+timedelta(i) for i in range(5)]
target = list(drange(date(2010,6,1), date(2010,8,31)))
all_dates = sorted(set(pre) | set(base_days) | set(post) | set(target))
print("counts:", len(pre), len(base_days), len(post), len(target), len(all_dates))

names = ['sst_%s.nc' % d.strftime('%Y%m%d') for d in all_dates]
print("total files:", len(names), "est MB:", len(names)*193370/1e6)

# verify all exist remotely (cheap list of a few), and test timed parallel download of 20 files
def one(nm):
    fs.get(base + '/' + nm, '/work/data/' + nm)
    return nm
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(one, names[:20]))
dt = time.time() - t0
print("20 files in %.2fs -> %.1f files/s" % (dt, 20/dt))
