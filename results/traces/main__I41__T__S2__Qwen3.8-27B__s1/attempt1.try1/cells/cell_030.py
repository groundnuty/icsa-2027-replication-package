import numpy as np
wt = np.load("work/target.npz"); wm = np.load("work/mhw.npy")
sea = wt["sea"]
print("sea cells with >=1 MHW day:", int((wm.sum(axis=0).reshape(60,60)[sea] > 0).sum()), "of 3308")
print("active day count:", int(wm.astype(bool).any(axis=(1,2)).sum()))
