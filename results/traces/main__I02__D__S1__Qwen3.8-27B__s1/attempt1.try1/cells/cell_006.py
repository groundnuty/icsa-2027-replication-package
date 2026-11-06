import fsspec, os, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
baseline_dates = [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]
t0 = dt.date(2004,6,1); t1 = dt.date(2004,8,31)
target_dates = [t0 + dt.timedelta(days=i) for i in range((t1-t0).days+1)]
names = [d.strftime('sst_%Y%m%d.nc') for d in baseline_dates+target_dates]

def fetch(nm):
    lp = f'/work/data/{nm}'
    if os.path.exists(lp) and os.path.getsize(lp) > 1000:
        return (nm, 'ok')
    try:
        fs.get(os.path.join(base, nm), lp)
        sz = os.path.getsize(lp)
        return (nm, 'ok' if sz > 1000 else 'TOOSMALL')
    except Exception as e:
        return (nm, f'ERR {e}')

t_start = time.time()
with ThreadPoolExecutor(max_workers=16) as ex:
    res = list(ex.map(fetch, names))
elapsed = time.time() - t_start
print(f"total {elapsed:.1f}s for {len(res)} files")
bad = [r for r in res if r[1] != 'ok']
print("bad count:", len(bad))
for b in bad[:20]: print(b)
