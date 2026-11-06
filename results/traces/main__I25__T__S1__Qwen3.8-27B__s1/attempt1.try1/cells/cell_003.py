
import fsspec, datetime as dt, time
fs = fsspec.filesystem('onedata')
t0=time.time()
# try walk to get all paths (may be slow); limit depth
count=0
allfiles=[]
for root, dirs, files in fs.walk('/icsa2027_data_20261101T090944Z/s1z'):
    for f in files:
        if f.endswith('.nc'):
            allfiles.append(f)
print("elapsed", time.time()-t0)
print("count:", len(allfiles))
print(sorted(allfiles)[:2], sorted(allfiles)[-2:])
