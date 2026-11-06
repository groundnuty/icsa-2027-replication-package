
import fsspec, os, time
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

fs = fsspec.filesystem('onedata')
remote_base = '/icsa2027_data_20261101T090944Z/s1z/'
local_dir = '/work/files'
os.makedirs(local_dir, exist_ok=True)

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += timedelta(days=1)
    return out

dates = sorted(set(
    daterange(date(1991,12,27), date(1991,12,31))
  + daterange(date(1992,1,1), date(2002,12,31))
  + daterange(date(2003,1,1), date(2003,1,5))
  + daterange(date(2008,6,1), date(2008,8,31))
))
print("total dates:", len(dates))

def fetch(d):
    name = f"sst_{d:%Y%m%d}.nc"
    local = os.path.join(local_dir, name)
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return (d, 'skip')
    for attempt in range(5):
        try:
            fs.get_file(remote_base + name, local)
            if os.path.getsize(local) > 0:
                return (d, 'ok')
        except Exception as e:
            err = e
        time.sleep(1 + attempt)
    return (d, 'FAIL:' + str(err)[:80])

t0 = time.time()
results = {}
done = 0
with ThreadPoolExecutor(max_workers=24) as ex:
    futs = {ex.submit(fetch, d): d for d in dates}
    for fut in as_completed(futs):
        d, status = fut.result()
        results[d] = status
        done += 1
        if done % 400 == 0:
            print(f"{done}/{len(dates)}  elapsed={time.time()-t0:.0f}s", flush=True)

fails = {d: s for d, s in results.items() if not s in ('ok','skip')}
print("done in", time.time()-t0, "s; failures:", fails)
nlocal = len([f for f in os.listdir(local_dir) if f.endswith('.nc')])
print("local files:", nlocal)
