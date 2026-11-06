import fsspec,re,datetime as dt,xarray as xr
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=sorted(fs.ls(p,detail=False))
names=[f.split('/')[-1] for f in fl]
print(names[0],names[-1],len(names))
ds=sorted(dt.datetime.strptime(n[4:12],'%Y%m%d').date() for n in names if re.match(r'sst_\d{8}\.nc',n))
print(len(ds),[n for n in names if not re.match(r'sst_\d{8}\.nc',n)])
s=set(ds);d=ds[0];miss=[]
while d<=ds[-1]:
    if d not in s:miss.append(d)
    d+=dt.timedelta(1)
print(len(miss),miss[:5],miss[-5:])
x=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf');print(x)