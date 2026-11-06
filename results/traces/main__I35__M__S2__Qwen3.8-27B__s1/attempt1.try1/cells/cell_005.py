import numpy as np, json
print("numpy:", np.__version__)
meta = json.load(open("/tmp/meta.json"))
p1 = np.load("/tmp/part1.npy")   # 1991-12-27..1996-12-31
p2 = np.load("/tmp/part2.npy")   # 1997-01-01..2003-01-05
p3 = np.load("/tmp/part3.npy")   # 2009-06-01..2009-08-31
print(p1.shape, p2.shape, p3.shape)

# sea cells: finite on every target day
finite_all = np.isfinite(p3).all(axis=0)
print("sea cells:", int(finite_all.sum()), "of", finite_all.size)
print("land/missing cells:", int((~finite_all).sum()))
# how many cells miss exactly k target days?
nmiss = (~np.isfinite(p3)).sum(axis=0)
import collections
print(collections.Counter(nmiss[~finite_all].tolist()).most_common(10))
# baseline candidate range
X = np.concatenate([p1, p2], axis=0)
print("candidate days:", X.shape)
# check any all-NaN candidate day (over sea cells only)
sea = finite_all
Xsea = X[:, sea]
allday_nan = (~np.isfinite(Xsea)).all(axis=1)
print("candidate days all-NaN over sea cells:", int(allday_nan.sum()))
np.save("/tmp/X.npy", X); np.save("/tmp/p3.npy", p3); np.save("/tmp/sea.npy", sea)
