import fsspec, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
import datetime as dt

# build required date lists
d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
baseline_dates = [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]
t0 = dt.date(2004,6,1); t1 = dt.date(2004,8,31)
target_dates = [t0 + dt.timedelta(days=i) for i in range((t1-t0).days+1)]
print(len(baseline_dates), len(target_dates), "total", len(baseline_dates)+len(target_dates))

names = [d.strftime('sst_%Y%m%d.nc') for d in baseline_dates+target_dates]
os.makedirs('/work/data', exist_ok=True)
# speed test: 30 files, 8 threads
def fetch(nm):
    lp = f'/work/data/{nm}'
    if os.path.exists(lp) and os.path.getsize(lp) > 1000:
        return (nm, 'cached')
    try:
        fs.get(os.path.join(base, nm), lp)
        return (nm, os.path.getsize(lp))
    except Exception as e:
        return (nm, f'ERR {e}')

t_start = time.time()
test = names[:30]
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(fetch, test))
elapsed = time.time() - t_start
print(f"30 files in {elapsed:.1f}s => {30/elapsed*60:.0f} files/min")
sizes = [r[1] for r in res if not isinstance(r[1], str) or r[1]=='cached']
errs = [r for r in res if isinstance(r[1], str) and r[1]!='cached']
print("errors:", errs[:5])
print("min size:", min(s for s in sizes if isinstance(s,int)))
