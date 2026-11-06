import fsspec
import os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.find(path)

# Now filter for sst_YYYYMMDD.nc
sst_files = [f for f in all_files if os.path.basename(f).startswith('sst_') and os.path.basename(f).endswith('.nc')]
sst_files.sort()

if sst_files:
    print(f"Total SST files: {len(sst_files)}")
    print(f"First: {sst_files[0]}")
    print(f"Last: {sst_files[-1]}")

    # Check for 2008 and 1992-2002
    target_2008 = [f for f in sst_files if '2008' in f]
    baseline_92_02 = [f for f in sst_files if any(str(y) in f for y in range(1992, 2003))]
    print(f"Files from 2008: {len(target_2008)}")
    print(f"Files from 1992-2002: {len(baseline_92_02)}")
else:
    print("No SST files found using fs.find.")
