import numpy as np
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
print("A shape:", A.shape)
d2i = {d: i for i, d in enumerate(dates)}
ext_n = d2i['2003-01-05'] + 1
ext = A[:ext_n]
print("ext shape:", ext.shape)
idx = np.where(np.ones(ext_n, bool))[0]
print("idx shape:", idx.shape, idx[:5])
p = ext[idx]
print("p shape:", p.shape)
an = np.all(np.isnan(p), axis=0)
print("an shape:", an.shape)
print("an[22,4]:", an[22,4])
c = np.count_nonzero(~an, axis=0)
print("c shape:", c.shape, "c[22,4]:", c[22,4])
ps = np.where(an, 0.0, p)
s = np.nansum(ps, axis=0)
print("s shape:", s.shape)
out = np.where(c > 0, s / np.maximum(c, 1), np.nan)
print("out shape:", out.shape, "out[22,4]:", out[22,4])
