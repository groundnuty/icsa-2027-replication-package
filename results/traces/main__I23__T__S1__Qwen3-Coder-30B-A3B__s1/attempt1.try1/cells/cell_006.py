import fsspec
import os

fs = fsspec.filesystem('onedata')
base_path = '/icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base_path)

print(f"Number of files found: {len(files)}")
print("First 10 files:")
for i, f in enumerate(files[:10]):
    print(f"  {f}")

# Check if we can access a specific file
if len(files) > 0:
    sample_file = files[0]
    print(f"\nSample file: {sample_file}")
    
    # Try to get file attributes to extract date
    try:
        attrs = fs.info(sample_file)
        print(f"File info keys: {list(attrs.keys())}")
    except Exception as e:
        print(f"Error getting file info: {e}")