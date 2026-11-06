import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')

# Let's examine the structure of one file
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", ds.dims)
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    if 'sst' in ds.data_vars:
        print("SST shape:", ds.sst.shape)
        print("SST coordinates:", ds.sst.coords)
    print("Lat range:", ds.latitude.min().values, "to", ds.latitude.max().values)
    print("Lon range:", ds.longitude.min().values, "to", ds.longitude.max().values)