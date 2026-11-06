import datetime as dt, os, fsspec, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)

def daterange(a, b):
    cur = a
    while cur <= b:
        yield cur
        cur += dt.timedelta(days=1)

dl1 = list(daterange(dt.date(1991,12,27), dt.date(1996,12,31)))
dl2 = list(daterange(dt.date(1997,1,1), dt.date(2003,1,5)))
dl3 = list(daterange(dt.date(2012,6,1), dt.date(2012,8,31)))
print(len(dl1), len(dl2), len(dl3), "=", len(dl1)+len(dl2)+len(dl3))

def download_batch(dl, tag):
    t0 = time.time()
    n = 0
    for d in dl:
        name = f"sst_{d:%Y%m%d}.nc"
        dst = f"/work/data/{name}"
        if not os.path.exists(dst):
            fs.get(f"{base}/{name}", dst)
            n += 1
    print(f"{tag}: {n} new, {len(dl)} total, {time.time()-t0:.1f}s", flush=True)

download_batch(dl1, "1991-12-27..1996-12-31")
