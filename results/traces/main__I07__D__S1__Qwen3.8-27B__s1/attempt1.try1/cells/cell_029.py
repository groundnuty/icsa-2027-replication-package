import numpy as np
from datetime import date, timedelta
S_tgt = np.load('/work/S_tgt.npy'); thr_s = np.load('/work/thr_s.npy'); mask = np.load('/work/mask.npy')
tgt_dates = []
d = date(2021,6,1)
while d <= date(2021,8,31):
    tgt_dates.append(d); d += timedelta(days=1)
def doy_of(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1
doy_tgt = np.array([doy_of(dt) for dt in tgt_dates])
sea = np.isfinite(S_tgt).all(axis=0).reshape(-1)
thr_tgt = thr_s[doy_tgt-1].reshape(92, 60, 60)
hot = S_tgt >= thr_tgt

# cells active on June 1 must be hot June1..June5 (run starts at window start)
act0 = mask[0].reshape(-1)
c0 = np.where(act0 & sea)[0]
print("cells active Jun1:", len(c0))
print("all hot on days 0..4:", (hot[0:5].reshape(5, 3600)[:, c0].all(axis=0)).all())

# cells active Aug 8 (idx 68): hot on Aug 8
act68 = mask[68].reshape(-1)
c68 = np.where(act68 & sea)[0]
print("cells active Aug8:", len(c68), "hot that day:", hot[68].reshape(-1)[c68].all())
# nothing active after Aug 8
print("mask days 69.. all zero:", mask[69:].sum() == 0)
# check per-day active counts around the end
counts = mask.reshape(92, -1).sum(axis=1)
for i in range(64, 92):
    print(tgt_dates[i], "active cells:", counts[i])
