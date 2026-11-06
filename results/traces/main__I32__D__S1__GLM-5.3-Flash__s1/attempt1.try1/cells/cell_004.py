import fsspec
fs = fsspec.filesystem('onedata')
g2 = fs.glob('icsa2027_data_20261101T090944Z/s2z/*')
print(len(g2), g2[0], g2[-1])
g1 = fs.glob('icsa2027_data_20261101T090944Z/s1z/*')
print(len(g1), g1[0], g1[-1])
# ranges
import re
def rng(g):
    ds = sorted(f.split('/')[-1][4:12] for f in g)
    return ds[0], ds[-1]
print('s1z', rng(g1))
print('s2z', rng(g2))
# check specific dates
names = set(f.split('/')[-1] for f in g1) | set(f.split('/')[-1] for f in g2)
for d in ['19911227','19911231','19920101','20021231','20030101','20030105','20050601','20050831','20040229']:
    print(d, ('sst_'+d+'.nc') in names)
