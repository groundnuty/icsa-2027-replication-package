import os
files=sorted(os.listdir(d)); print(files[0],files[-1], len(files)); print([f for f in files if not f.startswith('sst_')][:5])
dates=[f[4:12] for f in files if f.startswith('sst_')]
print(len(dates), dates[0], dates[-1])
import collections
print(sorted(collections.Counter(x[:4] for x in dates).items())[:50])