import fsspec, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)
import datetime as dt
def datestr(d): return d.strftime('%Y%m%d')
def check(d):
    name = f"_{d.strftime('%Y%m%d')}.nc"
    try:
        fs.exists(base + f"/sst_{d.strftime('%Y%m%d')}.nc")
        return (d, True)
    except Exception as e:
        return (d, False)

# build the full list of required dates
base_start = dt.date(1991,12,27)
base_end   = dt.date(2003,1,5)
tgt_start  = dt.date(2019,6,1)
tgt_end    = dt.date(2019,8,31)
dates = []
d = base_start
while d <= base_end:
    dates.append(d); d += dt.timedelta(days=1)
t = tgt_start
while t <= tgt_end:
    dates.append(t); t += dt.timedelta(days=1)
print("required files:", len(dates))

# existence check of all in parallel
with ThreadPoolExecutor(max_workers=32) as ex:
    results = list(ex.map(check, dates))
missing = [d for d, ok in results if not ok]
print("missing:", len(missing), missing[:20])
