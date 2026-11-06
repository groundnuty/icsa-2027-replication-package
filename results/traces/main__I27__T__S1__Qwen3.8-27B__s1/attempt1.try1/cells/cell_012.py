
import fsspec, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
BASE = '/icsa2027_data_20261101T090944Z/s1z'
start = dt.date(1991,12,27); end = dt.date(2003,1,5)
all_dates = [start + dt.timedelta(days=i) for i in range((end-start).days+1)]
print("baseline+edge dates:", len(all_dates))
def ex(d):
    return fs.exists(f"{BASE}/sst_{d.strftime('%Y%m%d')}.nc")
missing = []
with ThreadPoolExecutor(max_workers=16) as exm:
    for d, ok in zip(all_dates, exm.map(ex, all_dates)):
        if not ok: missing.append(str(d))
print("missing:", missing)
import numpy as np
np.save('/tmp/mhw/bdates.npy', np.array([d.toordinal() for d in all_dates]))
