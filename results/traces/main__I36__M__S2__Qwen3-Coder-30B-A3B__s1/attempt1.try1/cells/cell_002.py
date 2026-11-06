import os
print("Contents of /data/icsa2027_data_20261101T090944Z/s2z/:")
for root, dirs, files in os.walk("/data/icsa2027_data_20261101T090944Z/s2z"):
    for file in files:
        print(os.path.join(root, file))