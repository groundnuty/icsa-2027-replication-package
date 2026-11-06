
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
import collections
print(len(files))
names=[f.split('/')[-1] for f in files]
print(collections.Counter(n[:4] for n in names))
print([n for n in names if not n.startswith('sst_')][:10])
print(names[-3:])
with fs.open(files[0],'rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf'); ds.load()
print(ds)
