import os, time
p = '/work/data/sst_s2.nc'
if os.path.exists(p):
    print("size so far:", os.path.getsize(p), "of 3785412176")
print(open('/work/dl.log').read()[-500:])