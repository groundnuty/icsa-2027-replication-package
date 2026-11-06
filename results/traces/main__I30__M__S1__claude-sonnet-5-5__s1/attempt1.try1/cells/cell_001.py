import os
for r,d,f in os.walk('/data/icsa2027_data_20261101T090944Z/s1z'):
    print(r,len(f),f[:5],f[-3:])