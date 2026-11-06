import xarray as xr,os
fl=fs.ls('icsa2027_data_20261101T090944Z/s1z')
names=sorted(os.path.basename(f) for f in fl)
print(len(names),names[0],names[-1],[n for n in names if not n.startswith('sst_')][:5])
os.makedirs('/work/d',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s1z/'+names[0],'/work/d/a.nc')
d=xr.open_dataset('/work/d/a.nc',engine='h5netcdf');print(d)