import os

# Check the exact file naming pattern
path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(path_s1z))[:20]  # First 20 files

print("First 20 filenames:")
for f in files:
    print(f)

# Check if there are any files from 1992-2002
print("\nFiles from 1992-2002:")
for f in files:
    if f.startswith("sst_199") or f.startswith("sst_200"):
        print(f)
        
# Check for 2021 files
print("\nFiles from 2021:")
for f in files:
    if f.startswith("sst_2021"):
        print(f)