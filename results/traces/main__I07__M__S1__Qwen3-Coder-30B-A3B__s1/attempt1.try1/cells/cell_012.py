import xarray as xr
import os

# Try to load a specific file to make sure it works
path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
file_path = os.path.join(path_s1z, "sst_19920101.nc")

print(f"Trying to load: {file_path}")
try:
    ds = xr.open_dataset(file_path, engine="h5netcdf")
    print("Success!")
    print("Dataset info:")
    print(f"  Shape: {ds['analysed_sst'].shape}")
    print(f"  Coordinates: {list(ds.coords.keys())}")
    print(f"  Variables: {list(ds.data_vars.keys())}")
    ds.close()
except Exception as e:
    print(f"Error: {e}")
    
    # Try another approach - see if the file exists
    print(f"File exists: {os.path.exists(file_path)}")
    
    # Check what files are actually there
    files = sorted(os.listdir(path_s1z))
    print("Some files from 1992:")
    for f in files:
        if f.startswith("sst_1992"):
            print(f"  {f}")