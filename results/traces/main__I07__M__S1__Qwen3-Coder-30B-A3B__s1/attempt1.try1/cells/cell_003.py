import os
path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
path_s2z = "/data/icsa2027_data_20261101T090944Z/s2z"

print("Contents of s1z directory:")
try:
    print(os.listdir(path_s1z))
except Exception as e:
    print(f"Error: {e}")

print("\nContents of s2z directory:")
try:
    print(os.listdir(path_s2z))
except Exception as e:
    print(f"Error: {e}")