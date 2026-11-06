import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'

# Open one file to examine its structure
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nSST variable shape:", ds['sst'].shape)
    print("SST variable dims:", ds['sst'].dims)
    print("Lat range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
    print("Lon range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)
    print("Sample SST data:")
    print(ds['sst'].isel(time=0, lat=0, lon=0))