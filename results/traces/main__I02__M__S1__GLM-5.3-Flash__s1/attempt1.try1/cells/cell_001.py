import os
for root, dirs, files in os.walk('/data/icsa2027_data_20261101T090944Z/s1z'):
    print("ROOT:", root)
    print("dirs:", dirs[:20])
    print("n files:", len(files))
    for f in sorted(files)[:40]:
        print("  ", f, os.path.getsize(os.path.join(root,f)))
    break
