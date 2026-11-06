import fsspec

fs = fsspec.filesystem('onedata')
try:
    # List all files in the directory
    files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
    print(f"Total files: {len(files)}")
    print("First 10 files:")
    for i, f in enumerate(files[:10]):
        print(f"  {f}")
        
    # Try to read one file to verify
    if files:
        sample_file = files[0]
        print(f"\nTrying to read: {sample_file}")
        with fs.open(sample_file, 'rb') as f:
            import xarray as xr
            ds = xr.open_dataset(f, engine='h5netcdf')
            print(f"Successfully opened {sample_file}")
            print(f"Dimensions: {ds.dims}")
            ds.close()
except Exception as e:
    print(f"Error: {e}")