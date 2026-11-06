import fsspec, xarray as xr, traceback
fs = fsspec.filesystem('onedata')
try:
    with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print(ds)
        print()
        t = ds['time'].values
        print("time dtype:", t.dtype, "n:", len(t))
        print("first:", t[:5], "last:", t[-5:])
        print("lat:", ds.latitude.values.min(), ds.latitude.values.max(), ds.latitude.size)
        print("lon:", ds.longitude.values.min(), ds.longitude.values.max(), ds.longitude.size)
        print("encoding sst:", ds.analysed_sst.encoding)
except Exception:
    traceback.print_exc()
