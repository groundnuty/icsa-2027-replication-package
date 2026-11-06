import numpy as np
S_base = np.load('/work/S_base.npy')
M = np.load('/work/M.npy')
NC = 3600
flat = S_base.reshape(S_base.shape[0], NC)
S_tgt = np.load('/work/S_tgt.npy')
sea = np.isfinite(S_tgt).all(axis=0).reshape(-1)
c2 = int(np.where(sea)[0][-1])
print("c2:", c2, "row,col:", c2//60, c2%60)
d = 152
idx = np.where(M[d])[0]
col = flat[idx, c2]
print("n pool:", len(col), "n finite:", np.isfinite(col).sum(), "n nan:", np.isnan(col).sum())
# manual with NaN-aware sort
fin = col[np.isfinite(col)]
ps = np.sort(fin)
h = (len(fin)+1)*0.9
print("h:", h)
manual = ps[int(np.floor(h))-1] + (h-int(np.floor(h)))*(ps[int(np.floor(h))]-ps[int(np.floor(h))-1])
print("manual (nan-removed):", manual)
# what does numpy hazen give
print("numpy:", np.nanpercentile(col, 90, method='hazen'))
# and plain quantile on finite values
print("numpy on finite:", np.quantile(fin, 0.9, method='hazen'))
