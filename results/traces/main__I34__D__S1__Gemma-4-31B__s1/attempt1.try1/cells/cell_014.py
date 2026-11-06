import fsspec
import xarray as xr

fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

try:
    with fs.open(remote_path, 'rb') as f:
        # Try to open with xarray. Note: NetCDF4/HDF5 usually requires random access.
        # fsspec.open usually provides a file-like object that supports seek.
        with xr.open_dataset(f, engine='h5netcdf') as ds:
            print("Successfully opened with fs.open!")
            print(ds)
except Exception as e:
    print(f"Failed to open with fs.open: {e}")
