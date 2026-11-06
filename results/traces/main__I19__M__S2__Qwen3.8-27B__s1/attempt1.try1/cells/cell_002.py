import os
p = '/data/icsa2027_data_20261101T090944Z'
for root, dirs, files in os.walk(p):
    for f in files[:20]:
        print(os.path.join(root, f))
    if len(dirs) > 5:
        dirs[:] = []
        break
print("done")
