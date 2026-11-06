import numpy as np
S_base = np.load('/work/S_base.npy')
M = np.load('/work/M.npy')
NC = 3600
flat = S_base.reshape(S_base.shape[0], NC)
d = 152
idx = np.where(M[d])[0]
ok = True
for c in (0, 3599, 1000, 2000, 1234):
    col = flat[idx, c]
    ps = np.sort(col)
    n = len(col); p = 0.9
    i_star = n*p + 0.5          # 1-based virtual position (Hazen)
    i = int(np.floor(i_star))
    g = i_star - i
    manual = ps[i-1] + g*(ps[i]-ps[i-1])
    npval = np.nanpercentile(col, 90, method='hazen')
    ok &= np.isclose(manual, npval)
    print(c, "manual:", manual, "numpy:", npval, "match:", np.isclose(manual, npval))
print("ALL MATCH:", ok)
# and confirm it's NOT 'linear'
lin = np.nanpercentile(flat[idx,0], 90, method='linear')
haz = np.nanpercentile(flat[idx,0], 90, method='hazen')
print("linear vs hazen differ:", lin, haz, lin != haz)
