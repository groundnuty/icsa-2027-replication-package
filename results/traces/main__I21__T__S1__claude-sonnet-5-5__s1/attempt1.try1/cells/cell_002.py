fl=sorted(fs.ls(p,detail=False))
names=[f.split('/')[-1] for f in fl]
print(names[0],names[-1],len(names))
import re,datetime as dt
ds=sorted(dt.datetime.strptime(n[4:12],'%Y%m%d').date() for n in names if re.match(r'sst_\d{8}\.nc',n))
print(len(ds),[n for n in names if not re.match(r'sst_\d{8}\.nc',n)])
# gaps
d0=dt.date(1991,12,27);
miss=[]
s=set(ds);d=ds[0]
while d<=ds[-1]:
    if d not in s:miss.append(d)
    d+=dt.timedelta(1)
print(len(miss),miss[:5],miss[-5:])
f=fs.open(fl[0],'rb')
import xarray as xr
x=xr.open_dataset(f,engine='h5netcdf');print(x)