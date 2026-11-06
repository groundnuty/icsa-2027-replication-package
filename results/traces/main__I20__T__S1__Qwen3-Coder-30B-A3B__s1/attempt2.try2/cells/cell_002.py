import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
# Open one file to understand the structure
with fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", ds.dims)
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:")
    for coord in ds.coords:
        print(f"  {coord}: {ds.coords[coord].shape}")
    if 'sst' in ds.data_vars:
        print("SST variable shape:", ds.sst.shape)
        print("SST variable dtype:", ds.sst.dtype)
        print("SST coordinates:", ds.sst.coords)
    ds.close()