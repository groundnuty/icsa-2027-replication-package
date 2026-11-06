import xarray as xr, numpy as np, glob
D='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(D+'/sst_19820101.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs)
fs=sorted(os.listdir(D)); print(fs[0],fs[-1]); print(len(fs))
print(subprocess.run(f"ls {D} | grep -v '^sst_' | head",shell=True,capture_output=True,text=True).stdout)