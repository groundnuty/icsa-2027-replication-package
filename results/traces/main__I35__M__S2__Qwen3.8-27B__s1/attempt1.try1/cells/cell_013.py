import numpy as np
M = np.load("/tmp/M.npy")
X = np.load("/tmp/X.npy")
cand = np.datetime64("1991-12-27") + np.arange(X.shape[0])

def idx(s):
    return int(np.searchsorted(cand, np.datetime64(s)))

for s in ["1992-02-24","1992-02-28","1992-02-29","1992-03-01","1992-03-05","1992-03-06","1992-03-07"]:
    k = idx(s)
    print(s, "row59(doy60):", M[59, k], " rows containing:", (np.where(M[:, k])[0]+1).tolist())
