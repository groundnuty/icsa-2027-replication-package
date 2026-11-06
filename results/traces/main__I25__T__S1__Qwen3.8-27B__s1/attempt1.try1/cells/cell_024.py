
import fsspec, io, numpy as np, xarray as xr
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
ref_lat=None; ref_lon=None
for name in ['sst_19911227.nc','sst_19960718.nc','sst_20021231.nc','sst_20030105.nc','sst_20160601.nc','sst_20160831.nc']:
    raw = fs.cat_file(base+name)
    ds = xr.open_dataset(io.BytesIO(raw), engine='h5netcdf')
    lat = ds.latitude.values; lon = ds.longitude.values
    print(name, lat.dtype, lat.shape, lon.shape, "shape sst:", ds.analysed_sst.shape, "time:", ds.time.values[0])
    if ref_lat is None:
        ref_lat, ref_lon = lat.copy(), lon.copy()
    else:
        print("  lat identical:", bool((lat==ref_lat).all()), "lon identical:", bool((lon==ref_lon).all()))
    ds.close()
