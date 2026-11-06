import os
path = "/data/icsa2027_data_20261101T090944Z/s1z"
print("Contents of s1z directory:")
try:
    contents = os.listdir(path)
    print(contents)
except Exception as e:
    print(f"Error reading directory: {e}")