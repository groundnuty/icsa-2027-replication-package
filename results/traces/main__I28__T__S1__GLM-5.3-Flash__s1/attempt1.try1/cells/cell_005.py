import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for nm in ['sst_20130601.nc','sst_19920101.nc']:
    with fs.open(f'{base}/{nm}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print("=====", nm, "=====")
        print(ds)
        print("encoding sst:", {k:v for k,v in ds['sst'].encoding.items() if k in ('_FillValue','dtype','scale_factor','add_offset')})
        print("attrs sst:", ds['sst'].attrs)
        print("global attrs:", {k:str(v)[:80] for k,v in ds.attrs.items()})
        ds.close()
