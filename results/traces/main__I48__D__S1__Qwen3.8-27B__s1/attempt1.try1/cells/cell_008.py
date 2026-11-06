import os, datetime, concurrent.futures as cf, time
import fsspec
fs = fsspec.filesystem('onedata')
BASE = 'icsa2027_data_20261101T090944Z/s1z'
LOCAL = '/work/data'
os.makedirs(LOCAL, exist_ok=True)

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += datetime.timedelta(days=1)

ext_start = datetime.date(1991, 12, 27)
ext_end   = datetime.date(2003, 1, 5)
tgt_start = datetime.date(2016, 6, 1)
tgt_end   = datetime.date(2016, 8, 31)
all_dates = list(daterange(ext_start, ext_end)) + list(daterange(tgt_start, tgt_end))
print("total needed files:", len(all_dates))

def fname(d): return f"{LOCAL}/sst_{d.strftime('%Y%m%d')}.nc"

def download(d):
    src = f"{BASE}/sst_{d.strftime('%Y%m%d')}.nc"
    dst = fname(d)
    for attempt in range(6):
        try:
            fs.get(src, dst)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                return d, True
        except Exception as e:
            err = e
        time.sleep(1.5 * (attempt + 1))
    return d, False

def run_batch(dates, workers=16, tag=""):
    t0 = time.time()
    ok, fail = 0, []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (d, success) in enumerate(ex.map(download, dates), 1):
            if success: ok += 1
            else: fail.append(d)
            if i % 400 == 0:
                print(f"{tag} progress {i}/{len(dates)} ok={ok} fail={len(fail)} elapsed={time.time()-t0:.0f}s", flush=True)
    print(f"{tag} done: ok={ok} fail={len(fail)} elapsed={time.time()-t0:.0f}s", flush=True)
    return fail

# batch 1: first 900 of the extended baseline
fail1 = run_batch(all_dates[:900], tag="B1")
print("fail1:", fail1[:10])
with open('/work/data/batch1_fail.txt', 'w') as f:
    f.write("\n".join(str(d) for d in fail1))
