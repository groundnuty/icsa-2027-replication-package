
import fsspec, re, xarray as xr, collections
fs = fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
names=[f.split('/')[-1] for f in fs.ls(D, detail=False)]
print(len(names), names[0], names[-1])
print(collections.Counter(n[4:8] for n in names))
for p in [D+'/sst_19920101.nc', D+'/sst_20040601.nc', D+'/sst_20040831.nc']:
    print(p, fs.exists(p))
with fs.open(D+'/sst_20040601.nc','rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf')
    print(ds.analysed_sst.encoding, ds.analysed_sst.attrs)
