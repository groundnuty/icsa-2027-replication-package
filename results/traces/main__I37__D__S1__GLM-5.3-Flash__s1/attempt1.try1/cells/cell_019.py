import datetime as dt, os, fsspec, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def daterange(a, b):
    cur = a
    while cur <= b:
        yield cur
        cur += dt.timedelta(days=1)

dl2 = list(daterange(dt.date(1997,1,1), dt.date(2003,1,5)))
dl3 = list(daterange(dt.date(2012,6,1), dt.date(2012,8,31)))

def download_batch(dl, tag):
    t0 = time.time(); n = 0
    for d in dl:
        name = f"sst_{d:%Y%m%d}.nc"
        dst = f"/work/data/{name}"
        if not os.path.exists(dst):
            fs.get(f"{base}/{name}", dst); n += 1
    print(f"{tag}: {n} new, {len(dl)} total, {time.time()-t0:.1f}s", flush=True)

download_batch(dl2, "1997-01-01..2003-01-05")
download_batch(dl3, "2012-06-01..2012-08-31")
