import fsspec, xarray as xr, numpy as np, traceback
fs = fsspec.filesystem('onedata')
try:
    info = fs.info('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc')
    print("file info:", info)
except Exception:
    traceback.print_exc()

with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("units:", ds.analysed_sst.attrs)
    lat = ds.latitude.values.astype('float64')
    lon = ds.longitude.values.astype('float64')
    print("lat[:6]", lat[:6], "lat step uniq:", np.unique(np.round(np.diff(lat),6))[:5])
    print("lon[:6]", lon[:6], "lon step uniq:", np.unique(np.round(np.diff(lon),6))[:5])
    latmask = (lat >= 56.13 - 1e-6) & (lat <= 57.33 + 1e-6)
    lonmask = (lon >= 17.71 - 1e-6) & (lon <= 18.91 + 1e-6)
    print("n lat cells:", latmask.sum(), lat[latmask][[0,-1]])
    print("n lon cells:", lonmask.sum(), lon[lonmask][[0,-1]])
