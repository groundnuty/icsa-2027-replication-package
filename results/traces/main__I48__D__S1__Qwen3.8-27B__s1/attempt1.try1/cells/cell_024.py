import numpy as np
mask = np.load('/work/mask.npy')
tgt = np.load('/work/tgt.npy'); thr = np.load('/work/thr.npy'); sea = np.load('/work/sea_mask.npy')
doy = np.arange(153, 245)
hot = np.zeros_like(mask, dtype=bool)
hot[:, sea] = tgt[:, sea] >= thr[doy-1][:, sea]

c = 45
print("sea:", sea[c])
print("days 50..70  hot / mask / sst / thr:")
for d in range(50, 71):
    print(d, "hot" if hot[d,c] else "   ", "M" if mask[d,c] else " ", 
          f"{tgt[d,c]:.3f}", f"{thr[doy[d]-1, c]:.3f}", "HOT!" if tgt[d,c] >= thr[doy[d]-1, c] else "")
