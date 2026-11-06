import xarray as xr
names=set()
r=fs.ls('icsa2027_data_20261101T090944Z/s1z',detail=False)
print(r[-1])
for p in ['sst_19911227','sst_20030105','sst_20170601','sst_20170831']:
    print(p,fs.exists(f'icsa2027_data_20261101T090944Z/s1z/{p}.nc'))
ds=xr.open_dataset(fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc','rb'),engine='h5netcdf');print(ds)