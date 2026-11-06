import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
# check Dec 31 of last year and Feb 29 1996 files, plus exact file count
tests = ['sst_20191231.nc','sst_20151231.nc','sst_19960229.nc','sst_20000229.nc','sst_20040229.nc']
for p in tests:
    print(p, fs.exists(base+p))
import datetime
start = datetime.date(1982,1,1); end = datetime.date(2019,12,31)
n = (end-start).days+1
print('expected days', n)
