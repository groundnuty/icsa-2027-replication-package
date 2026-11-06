import numpy as np, fsspec, os, json, time, datetime as dt
print("numpy", np.__version__)
a = np.array([1.,2,3,4,5])
print("hazen ok:", np.quantile(a, 0.5, method='hazen'))

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/nc', exist_ok=True)

def daterange(d0, d1):
    cur = d0
    while cur <= d1:
        yield cur
        cur += dt.timedelta(days=1)

needed = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5))) + \
         list(daterange(dt.date(2019,6,1), dt.date(2019,8,31)))
print("files needed:", len(needed))

t0 = time.time()
missing = []
for i, d in enumerate(needed):
    fn = f"sst_{d.strftime('%Y%m%d')}.nc"
    lp = f"/work/nc/{fn}"
    if os.path.exists(lp) and os.path.getsize(lp) > 0:
        continue
    try:
        fs.get(f'{base}/{fn}', lp)
    except Exception as ex:
        missing.append(d.isoformat())
        print("FAIL", fn, type(ex).__name__)
    if i % 500 == 0:
        print(i, d, f"{time.time()-t0:.0f}s", flush=True)
print("done in", f"{time.time()-t0:.0f}s")
have = set(os.listdir('/work/nc'))
still_missing = [d.isoformat() for d in needed if f"sst_{d.strftime('%Y%m%d')}.nc" not in have]
print("n downloaded files:", len(have))
print("missing dates:", still_missing)
with open('/work/nc/manifest.json','w') as f:
    json.dump({"missing": still_missing}, f)
