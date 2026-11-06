
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print("\nDims:", dict(ds.sizes))
    print("\nCoords:", ds.coords)
    print("\nVariables:", list(ds.data_vars))
    print("\nTime range:", ds.time.values[0], ds.time.values[-1], len(ds.time))
    print("\nLat range:", ds.lat.values.min(), ds.lat.values.max(), len(ds.lat))
    print("\nLon range:", ds.lon.values.min(), ds.lon.values.max(), len(ds.lon))
