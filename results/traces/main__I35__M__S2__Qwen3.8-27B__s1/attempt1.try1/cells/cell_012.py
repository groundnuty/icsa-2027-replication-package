import numpy as np
M = np.load("/tmp/M.npy")
X = np.load("/tmp/X.npy")
cand = np.datetime64("1991-12-27") + np.arange(X.shape[0])

row60 = np.where(M[59])[0]   # doy 60 pool (unused anyway)
print("doy60 pool size:", len(row60))
print(sorted(set(str(c) for c in cand[row60])))
# expected per leap year: 02-24..03-06 (12 days) x3 = 36

# check doy 366 row
row366 = np.where(M[365])[0]
print("doy366 pool size:", len(row366))
print("first/last:", cand[row366[:3]], cand[row366[-3:]])
