
import fsspec, xarray as xr, collections
fs = fsspec.filesystem('onedata')
files = sorted(fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False))
print(len(files))
print(collections.Counter(f.split('/')[-1][:4] for f in files))
print(files[0], files[-1])
f=fs.open(files[0],'rb'); ds=xr.open_dataset(f,engine='h5netcdf'); print(ds)
