
import fsspec, os, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
local='/tmp/mhw_files'
os.makedirs(local, exist_ok=True)

def dlist(start, end):
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    return [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]

bdates = dlist('1991-12-27','2003-01-05')
tdates = dlist('2016-06-01','2016-08-31')
alldates = bdates + tdates
print("n files:", len(alldates))

def fetch(d):
    name = f"sst_{d.strftime('%Y%m%d')}.nc"
    lp = os.path.join(local, name)
    if os.path.exists(lp) and os.path.getsize(lp) > 0:
        return name, True
    for attempt in range(5):
        try:
            fs.get_file(base+name, lp)
            return name, os.path.exists(lp) and os.path.getsize(lp)>0
        except Exception as e:
            err = e
    print("FAIL", name, err)
    return name, False

t0=time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(fetch, alldates))
bad = [n for n,ok in res if not ok]
print("downloaded in %.1f s, bad: %d" % (time.time()-t0, len(bad)))
print(bad[:10])
