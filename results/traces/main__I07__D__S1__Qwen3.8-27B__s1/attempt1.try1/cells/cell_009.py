import fsspec, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)

def get_one(key):
    p = f"{base}/{key}"
    local = f"/work/data/{key}"
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return key, "skip", 0
    t0 = time.time()
    fs.get(p, local)
    return key, "ok", time.time()-t0

test = [f"sst_1992{m:02d}{d:02d}.nc" for m,d in [(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),(1,8),(1,9),(1,10)]]
t0 = time.time()
with ThreadPoolExecutor(max_workers=10) as ex:
    res = list(ex.map(get_one, test))
dt = time.time()-t0
print("10 files in", round(dt,2), "s; per-file:", [round(r[2],2) for r in res])
print("sizes:", [os.path.getsize(f"/work/data/{k}") for k,_,_ in res])
