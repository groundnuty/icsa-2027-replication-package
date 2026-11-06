import os
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
print(os.path.exists(path), os.path.getsize(path) if os.path.exists(path) else None)
