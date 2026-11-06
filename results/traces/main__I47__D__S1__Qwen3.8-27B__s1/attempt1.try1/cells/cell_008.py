import fsspec, os, time, datetime as dt, json
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)

base_start = dt.date(1991,12,27); base_end = dt.date(2003,1,5)
tgt_start  = dt.date(2019,6,1);   tgt_end  = dt.date(2019,8,31)
dates = []
d = base_start
while d <= base_end: dates.append(d); d += dt.timedelta(days=1)
t = tgt_start
while t <= tgt_end: dates.append(t); t += dt.timedelta(days=1)

t0 = time.time()
def dl(d):
    name = f"sst_{d.strftime('%Y%m%d')}.nc"
    dest = '/work/data/' + name
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return (name, 'cached')
    for attempt in range(3):
        try:
            fs.get(base + '/' + name, dest)
            return (name, 'ok')
        except Exception as e:
            if attempt == 2:
                return (name, f"FAIL {type(e).__name__}: {str(e)[:80]}")
            time.sleep(1 + attempt)

with ThreadPoolExecutor(max_workers=32) as ex:
    results = list(ex.map(dl, dates))

bad = [r for r in results if r[1] not in ('ok','cached')]
print("elapsed:", time.time()-t0, "s; total:", len(results), "bad:", len(bad))
print(bad[:10])
sizes = [os.path.getsize('/work/data/'+r[0]) for r in results if r[1] in ('ok','cached')]
import statistics
print("file size min/median/max:", min(sizes), statistics.median(sizes), max(sizes))
with open('/work/required_dates.json','w') as f:
    json.dump([d.strftime('%Y-%m-%d') for d in dates], f)
