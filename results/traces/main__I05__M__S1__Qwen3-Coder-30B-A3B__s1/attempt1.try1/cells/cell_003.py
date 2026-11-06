import os
path = "/data/icsa2027_data_20261101T090944Z/s1z"
print(f"Contents of {path}:")
try:
    print(os.listdir(path))
except Exception as e:
    print(f"Error: {e}")