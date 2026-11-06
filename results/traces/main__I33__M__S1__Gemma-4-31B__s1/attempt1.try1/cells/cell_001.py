import os

base_path = '/data/icsa2027_data_20261101T090944Z/s1z'
for root, dirs, files in os.walk(base_path):
    for file in files:
        print(os.path.join(root, file))
