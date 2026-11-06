import numpy as np
mhw = np.load('/work/mhw.npy')
sea = np.load('/work/sea.npy')
print("mhw dtype/shape:", mhw.dtype, mhw.shape, "total ones:", int(mhw.sum()))
sel = np.where(sea & (mhw.sum(axis=1)>0))[0]
print("num MHW cells:", len(sel), "first:", sel[:10])
c = sel[100]
print("c:", c, "sum:", int(mhw[c].sum()), "days with 1:", np.where(mhw[c]>0)[0])
print("trace check c=164:", int(mhw[164].sum()))
# check consistency: recompute hot & runs for c=164 vs mask
thr = np.load('/work/thr.npy'); target_arr = np.load('/work/target_arr.npy'); doy_target = np.load('/work/doy_target.npy')
h164 = (target_arr[:,164] >= thr[164, doy_target])
print("hot days 164:", np.where(h164)[0])
