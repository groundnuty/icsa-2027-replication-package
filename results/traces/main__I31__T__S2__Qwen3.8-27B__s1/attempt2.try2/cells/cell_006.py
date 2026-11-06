import fsspec, os, time
fs = fsspec.filesystem('onedata')
t0 = time.time()
with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f, open('~','wb') as out:
    n = 0
    while time.time() - t0 < 30:
        b = f.read(1 << 20)
        if not b: break
        out.write(b)
        n += len(b)
dt = time.time() - t0
print("read bytes:", n/1e6, "MB in", dt, "s ->", n/1e6/dt, "MB/s")
print("persist check file exists:", os.path.exists('~'))
