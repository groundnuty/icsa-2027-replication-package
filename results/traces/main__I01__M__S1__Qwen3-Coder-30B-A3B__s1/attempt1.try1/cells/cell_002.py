import os
print("Contents of /data/icsa2027_data_20261101T090944Z/s1z:")
s1z_path = "/data/icsa2027_data_20261101T090944Z/s1z"
files = os.listdir(s1z_path)
print(f"Number of files: {len(files)}")
print("First 10 files:")
for i, f in enumerate(files[:10]):
    print(f"  {f}")