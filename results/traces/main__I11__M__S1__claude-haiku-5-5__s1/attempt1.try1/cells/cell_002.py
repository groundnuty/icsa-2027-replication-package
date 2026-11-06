import xarray as xr, numpy as np, glob
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(d+'/sst_19820101.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs)
files=sorted(os.listdir(d)); print(files[0],files[-1], len(files)); print([f for f in files if not f.startswith('sst_')][:5])