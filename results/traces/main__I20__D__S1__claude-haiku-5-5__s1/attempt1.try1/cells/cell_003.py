import fsspec, re, os, datetime as dt
import xarray as xr
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names = sorted(f.split('/')[-1] for f in files)
print(len(names), names[0], names[-1])
other=[n for n in names if not re.match(r'sst_\d{8}\.nc$',n)]
print(other[:20])
dates=set(re.findall(r'sst_(\d{8})\.nc',' '.join(names)))
need=[]
d=dt.date(1991,12,27)
while d<=dt.date(2012,8,31):
    need.append(d.strftime('%Y%m%d')); d+=dt.timedelta(1)
print(len(need), sum(1 for x in need if x not in dates), [x for x in need if x not in dates][:10])
os.makedirs('/work/s',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc','/work/s/test.nc')
ds=xr.open_dataset('/work/s/test.nc',engine='h5netcdf'); print(ds)