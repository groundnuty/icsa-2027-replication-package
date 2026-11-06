import fsspec,re,datetime as dt
fs=fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
fl=fs.ls(P)
names=sorted(f.split('/')[-1] for f in fl)
print(len(names),names[0],names[-1],[n for n in names if not re.match(r'sst_\d{8}\.nc$',n)])
ds={dt.datetime.strptime(n[4:12],'%Y%m%d').date() for n in names if re.match(r'sst_\d{8}\.nc$',n)}
def rng(a,b):
    d=a;o=[]
    while d<=b:
        if d not in ds:o.append(d)
        d+=dt.timedelta(1)
    return o
print(rng(dt.date(1991,12,27),dt.date(2003,1,5)),rng(dt.date(2005,6,1),dt.date(2005,8,31)))
fs.get(P+'sst_20050601.nc','/work/a.nc')
import xarray as xr
x=xr.open_dataset('/work/a.nc',engine='h5netcdf');print(x)