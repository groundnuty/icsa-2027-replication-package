import numpy as np
thr = np.load('/work/thr.npy'); sea = np.load('/work/sea.npy')
target_arr = np.load('/work/target_arr.npy'); doy_target = np.load('/work/doy_target.npy')
print("dtypes:", thr.dtype, sea.dtype, target_arr.dtype, doy_target.dtype)
h = (target_arr.T >= thr[:, doy_target]) & np.isfinite(target_arr.T) & sea[:, None]
print("hot dtype:", h.dtype, "shape", h.shape)
h164 = h[164]
print("h164:", h164.astype(int).tolist())
pad = np.r_[False, h164, False]
print("pad dtype:", pad.dtype)
print("pad[:]:", pad.astype(int).tolist())
d = np.diff(pad)
print("d:", d.tolist())
print("d==1:", np.where(d==1)[0], "d==-1:", np.where(d==-1)[0])
