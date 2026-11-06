
import numpy as np, sys, os, time
print("numpy", np.__version__, "python", sys.version)
os.makedirs("/work", exist_ok=True)
with open("/work/marker.txt","w") as f: f.write("persist-test-123")
GLOBAL_MARKER = "hello-global"
# quick nanquantile method test
x = np.array([1.,2.,3.,4.,5.])
print("hazen p90 of 1..5:", np.nanquantile(x, 0.9, method="hazen"))  # hazen h=(n+1)p=5.4 -> 4 + 0.4*(5-4)=4.4? (n=5): h=(5+1)*0.9=5.4 -> between x[4]=5 and x[5] (oob) -> 5.0
import datetime
print("tm_yday 2021-02-28:", datetime.date(2021,2,28).timetuple().tm_yday, "2020-02-29:", datetime.date(2020,2,29).timetuple().tm_yday, "2021-03-01:", datetime.date(2021,3,1).timetuple().tm_yday)
t0=time.time()
import fsspec
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
fs.head(base+"sst_20210601.nc")
print("head latency:", time.time()-t0)
