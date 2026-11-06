import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(f"Total files: {len(files)}")
print(f"First few: {files[:5]}")
print(f"Last few: {files[-5:]}")
