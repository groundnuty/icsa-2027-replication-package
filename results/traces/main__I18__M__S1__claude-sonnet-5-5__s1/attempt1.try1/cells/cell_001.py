import os
d='/data/icsa2027_data_20261101T090944Z/s1z'
for r,_,f in os.walk(d):print(r,len(f),f[:5])