import xarray as xr
base='icsa2027_data_20261101T090944Z/s1z/'
for n in ['sst_19920101.nc','sst_20070601.nc']:
    try:
        with fs.open(base+n,'rb') as f:
            ds=xr.open_dataset(f,engine='h5netcdf').load()
            print(n, ds)
    except Exception as e: print(n, repr(e)[:300])