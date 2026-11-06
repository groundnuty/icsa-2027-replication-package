import fsspec,os,collections
fs = fsspec.filesystem('onedata')
g = fs.glob('icsa2027_data_20261101T090944Z/s1z/sst_*.nc')
print(len(g))
gn=sorted(os.path.basename(x) for x in g)
print(gn[0], gn[-1])
print(sorted(collections.Counter(n[4:8] for n in gn).items()))