
import numpy as np, datetime as dt
thr_raw = np.load('/tmp/mhw/thr_raw.npy')
thr_s = np.load('/tmp/mhw/thr_s.npy')
maskA = np.load('/tmp/mhw/maskA.npy')
hot = np.load('/tmp/mhw/hot.npy')
sea2 = np.load('/tmp/mhw/sea2.npy')
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(92)]
c = np.where(sea2)[0][0]
# wrap check at doy idx 4 (day 5): window days idx (4-15..4+15) mod 366 = 355..365, 0..19
idxw = [(4 + j) % 366 for j in range(-15, 16)]
expect = thr_raw[idxw, c].mean()
print("wrap smooth check:", thr_s[4, c], expect, np.isclose(thr_s[4,c], expect))
# and at idx 0
idxw0 = [(0 + j) % 366 for j in range(-15, 16)]
print("idx0 check:", np.isclose(thr_s[0,c], thr_raw[idxw0,c].mean()))
# day 60 handling: thr_s[59] should be mean of 31-window of (.., thr_raw[58], (thr_raw[58]+thr_raw[60])/2, thr_raw[60], ..)
idxw59 = [(59 + j) % 366 for j in range(-15, 16)]
print("idx59 check:", np.isclose(thr_s[59,c], thr_raw[idxw59,c].mean()))

active = maskA.any(axis=1)
print("--- first 16 days ---")
for k in range(16):
    print(tdates[k], "hot:", int(hot[k].sum()), "mhw:", int(maskA[k].sum()), "active:", bool(active[k]))
