
import fsspec, time
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
def exists(d):
    p = f"{base}/sst_{d}.nc"
    try:
        return fs.exists(p)
    except Exception as e:
        return f"ERR {e}"
tests = ['19920101','19921231','20020101','20021231','20030105','20080601','20080831','20080701','19840930','19911227']
t0=time.time()
for d in tests:
    print(d, exists(d))
print("elapsed", time.time()-t0)
