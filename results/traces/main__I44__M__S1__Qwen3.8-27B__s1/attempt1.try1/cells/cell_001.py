import os
d = "/data/icsa2027_data_20261101T090944Z/s1z"
print(os.path.isdir(d))
for e in sorted(os.listdir(d))[:50]:
    print(e)
print("count:", len(os.listdir(d)))
