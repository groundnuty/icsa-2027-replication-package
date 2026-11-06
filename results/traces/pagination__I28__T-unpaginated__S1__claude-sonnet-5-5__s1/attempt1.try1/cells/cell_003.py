import fsspec,xarray as xr,re,pandas as pd
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=fs.find(p)
ds=sorted(re.findall(r'sst_(\d{8})',x)[0] for x in fl if re.search(r'sst_\d{8}',x))
print(len(fl),len(ds),ds[0],ds[-1])
full=pd.date_range(ds[0],ds[-1]).strftime('%Y%m%d')
miss=sorted(set(full)-set(ds));print(len(miss),[m for m in miss if '1991'<=m[:4]<='2003' or m[:6] in('201306','201307','201308')])
print([x for x in fl if not re.search(r'sst_\d{8}\.nc',x)])
d=xr.open_dataset(fs.open(p+'/sst_20130601.nc','rb'),engine='h5netcdf');print(d)