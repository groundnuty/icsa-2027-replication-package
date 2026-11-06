import xarray as xr, numpy as np, os, glob
D="/data/icsa2027_data_20261101T090944Z/s1z"
ds=xr.open_dataset(D+"/sst_19820101.nc",engine="h5netcdf")
print(ds)
for v in ds.variables: print(v, ds[v].attrs)
names=sorted(os.listdir(D)); print(names[-3:], len(names))
import collections
print(collections.Counter(n.split('_')[0] for n in names))