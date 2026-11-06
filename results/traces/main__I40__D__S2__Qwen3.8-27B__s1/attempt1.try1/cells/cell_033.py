import numpy as np
sea = np.load('/work/sea.npy')
print("sea shape:", sea.shape, sea.sum())
sea = sea.reshape(-1)
np.save('/work/sea.npy', sea)

V_tgt = np.load('/work/V_tgt.npy').astype(np.float64).reshape(92, 3600)
# verify sea consistency against per-day finite sets
perday = np.isfinite(V_tgt)
print("same finite set each day:", np.all(perday == perday[0:1]), "finite/day:", perday[0].sum())
thr_sm = np.load('/work/thr_sm.npy'); doys = np.load('/work/doys.npy')
t90 = thr_sm[doys-1]
hot = V_tgt >= t90
print("overall hot fraction (sea cells):", hot[:, sea].mean())
hc = hot[:, sea].sum(axis=1)
print("per-day hot sea-cells min/max:", hc.min(), hc.max())
print("thr NaN in target window sea cells:", int(np.isnan(t90[:, sea]).sum()))
np.save('/work/hot.npy', hot)
