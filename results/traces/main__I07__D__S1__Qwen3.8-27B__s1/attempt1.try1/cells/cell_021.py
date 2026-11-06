import numpy as np
S_base = np.load('/work/S_base.npy')
M = np.load('/work/M.npy')
NC = 3600
flat = S_base.reshape(S_base.shape[0], NC)
d = 152
idx = np.where(M[d])[0]

# proper Hazen (HF type 5): h = (n-1)p + 2/3 (1-based)
for c in (0, 3599, 1000, 2000):
    col = flat[idx, c]
    n = len(col); p = 0.9
    h = (n-1)*p + 2/3
    i = int(np.floor(h))
    if h == i:
        manual = col_sorted if False else np.sort(col)[i-1]
    else:
        ps = np.sort(col)
        manual = ps[i-1] + (h-i)*(ps[i]-ps[i-1])
    npval = np.nanpercentile(col, 90, method='hazen')
    print(c, "hazen h=", h, "manual:", manual, "numpy:", npval, "match:", np.isclose(manual, npval))
