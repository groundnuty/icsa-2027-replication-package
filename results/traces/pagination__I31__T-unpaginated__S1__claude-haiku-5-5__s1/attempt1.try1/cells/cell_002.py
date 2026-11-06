
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files)); import collections
print(collections.Counter(f.split('/')[-1][:4] for f in files))
print(sorted(files)[0], sorted(files)[-1])
others=[f for f in files if not f.split('/')[-1].startswith('sst_')]
print(others[:10])
f=fs.open(sorted(files)[0],'rb'); ds=xr.open_dataset(f,engine='h5netcdf'); print(ds); 
