import fsspec, os, time
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)

needed = []
d = date(1991,12,27)
while d <= date(2003,1,5):
    needed.append(d); d += timedelta(days=1)
d = date(2021,6,1)
while d <= date(2021,8,31):
    needed.append(d); d += timedelta(days=1)
print("total needed:", len(needed))

def fname(dt): return f"sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc"

def get_one(dt, attempt=0):
    k = fname(dt)
    local = f"/work/data/{k}"
    try:
        if os.path.exists(local) and os.path.getsize(local) > 0:
            return k, "skip"
    except OSError:
        pass
    try:
        fs.get(f"{base}/{k}", local)
        if not (os.path.exists(local) and os.path.getsize(local) > 0):
            raise IOError("empty download")
        return k, "ok"
    except Exception as e:
        if attempt < 5:
            time.sleep(1 + attempt)
            return get_one(dt, attempt+1)
        return k, f"FAIL:{type(e).__name__}:{str(e)[:80]}"

t0 = time.time()
failed = []
with ThreadPoolExecutor(max_workers=16) as ex:
    for k, status in ex.map(lambda dt: get_one(dt), needed):
        if status not in ("ok", "skip"):
            failed.append((k, status))
print("download done in", round(time.time()-t0,1), "s")
print("failed:", failed[:10], "count:", len(failed))
print("files on disk:", len(os.listdir('/work/data')))
