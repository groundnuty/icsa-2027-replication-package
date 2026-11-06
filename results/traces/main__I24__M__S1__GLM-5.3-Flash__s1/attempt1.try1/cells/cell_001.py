import os
for root, dirs, files in os.walk('/data/icsa2027_data_20261101T090944Z/s1z'):
    print(root, len(dirs), len(files))
    for f in files[:50]:
        print('  ', f)
    if len(files) > 50:
        print('   ...')
