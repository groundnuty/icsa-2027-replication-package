import xarray as xr
import fsspec

# Open a sample file to understand the structure
fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", ds.dims)
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    if 'analysed_sst' in ds.data_vars:
        print("Analysed SST shape:", ds.analysed_sst.shape)
        print("Analysed SST coordinates:", ds.analysed_sst.coords)
    print("First few latitudes:", ds.latitude.isel(latitude=slice(0, 5)).values)
    print("First few longitudes:", ds.longitude.isel(longitude=slice(0, 5)).values)
    # Check the actual data
    sst_data = ds.analysed_sst.isel(time=0)
    print("Sample SST data shape:", sst_data.shape)
    print("Sample SST data (first 5x5):")
    print(sst_data.isel(latitude=slice(0, 5), longitude=slice(0, 5)).values)