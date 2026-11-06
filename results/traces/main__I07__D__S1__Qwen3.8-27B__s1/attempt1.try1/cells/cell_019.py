import numpy as np
S_base = np.load('/work/S_base.npy')
M = np.load('/work/M.npy')
NC = 3600
flat = S_base.reshape(S_base.shape[0], NC)
sea = np.isfinite(np.load('/work/S_tgt.npy')).all(axis=0).reshape(-1)
c = int(np.argmax(sea))
d = 152
idx = np.where(M[d])[0]
thr_one = np.nanpercentile(flat[idx], 90, method='hazen', axis=0)
pool = S_base[idx, c//60, c%60]; ps = np.sort(pool)
h = (len(pool)+1)*0.9
manual = ps[int(np.floor(h))-1] + (h-int(np.floor(h)))*(ps[int(np.floor(h))]-ps[int(np.floor(h))-1])
print("numpy cell thr:", thr_one[c], "manual:", manual, "match:", np.isclose(thr_one[c], manual))
# also verify with a second cell
c2 = int(np.where(sea)[0][-1])
thr2 = np.nanpercentile(flat[idx], 90, method='hazen', axis=0)[c2]
pool2 = np.sort(S_base[idx, c2//60, c2%60])
manual2 = pool2[int(np.floor(h))-1] + (h-int(np.floor(h)))*(pool2[int(np.floor(h))]-pool2[int(np.floor(h))-1])
print("cell2 match:", np.isclose(thr2, manual2), thr2, manual2)
