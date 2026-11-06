import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')

# Let's examine one file to understand the structure
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates and variables:")
    print(ds.coords)
    print("\nVariables:")
    print(ds.data_vars)
    print("\nFirst few lat/lon values:")
    print("Lat:", ds.lat.values[:5])
    print("Lon:", ds.lon.values[:5])
    print("\nSST shape:", ds.sst.shape)
    print("SST sample values:", ds.sst.values[0, :5, :5])