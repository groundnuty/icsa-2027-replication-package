import os
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
print(os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else None)
