import numpy as np
thr_sm = np.load('/work/thr_sm.npy'); doys = np.load('/work/doys.npy'); sea = np.load('/work/sea.npy')
V_tgt = np.load('/work/V_tgt.npy').astype(np.float64).reshape(92, 3600)
t90 = thr_sm[doys-1]
hot = V_tgt >= t90
print("hot shape:", hot.shape)
print("overall hot fraction (sea cells):", hot[:, sea].mean())
hc = hot[:, sea].sum(axis=1)
print("per-day hot sea-cells min/max:", hc.min(), hc.max())
print("thr NaN in target window sea cells:", int(np.isnan(t90[:, sea]).sum()))
np.save('/work/hot.npy', hot)
np.save('/work/t90.npy', t90)
