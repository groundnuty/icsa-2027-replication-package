
import fsspec, time
fs = fsspec.filesystem('onedata')

# single file full read timing
t0=time.time()
with fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_19920101.nc',"rb") as f:
    data = f.read()
t1=time.time()
print("single file bytes:", len(data), "time: %.2f s" % (t1-t0))

# parallel test with 8 files
from concurrent.futures import ThreadPoolExecutor
files = ['sst_%04d%02d%02d.nc' % (1992,1,d) for d in range(1,17)]
def read(p):
    with fs.open('/icsa2027_data_20261101T090944Z/s1z/'+p, "rb") as f:
        return f.read()
t0=time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(read, files))
t1=time.time()
print("16 files, 8 workers: total MB = %.1f, time %.2f s, MB/s = %.1f" % (sum(map(len,res))/1e6, t1-t0, sum(map(len,res))/1e6/(t1-t0)))
