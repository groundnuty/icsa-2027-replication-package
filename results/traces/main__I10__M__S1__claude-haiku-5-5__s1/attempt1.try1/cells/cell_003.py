import os
fs=sorted(os.listdir(D)); print(fs[0],fs[-1],len(fs))
print([f for f in fs if not f.startswith('sst_')][:10])
import collections
print(collections.Counter(f[4:8] for f in fs).most_common(3), sorted(set(f[4:8] for f in fs))[:3], sorted(set(f[4:8] for f in fs))[-3:])