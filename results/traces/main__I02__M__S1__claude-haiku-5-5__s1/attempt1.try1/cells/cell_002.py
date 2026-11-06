import xarray as xr, numpy as np, glob
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(d+'/sst_19820101.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs, ds[v].encoding.get('_FillValue'))
files=sorted(os.listdir(d)); print(files[0],files[-1],len(files))
print(set(f[:4] for f in files))