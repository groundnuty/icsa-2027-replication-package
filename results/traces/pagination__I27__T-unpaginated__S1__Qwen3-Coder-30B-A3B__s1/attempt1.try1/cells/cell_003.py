import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
# Let's examine a sample file to understand the structure in detail
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", dict(ds.dims))
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:")
    for coord in ds.coords:
        print(f"  {coord}: shape={ds.coords[coord].shape}, values range={ds.coords[coord].min().values} to {ds.coords[coord].max().values}")
    
    if 'analysed_sst' in ds.data_vars:
        print("\nAnalysed SST info:")
        print(f"  Shape: {ds.analysed_sst.shape}")
        print(f"  Data type: {ds.analysed_sst.dtype}")
        print(f"  First few values: {ds.analysed_sst.isel(time=0, latitude=0, longitude=0)}")
        print(f"  Valid range: {ds.analysed_sst.min().values} to {ds.analysed_sst.max().values}")
    
    ds.close()