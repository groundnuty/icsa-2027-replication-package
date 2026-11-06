
import numpy as np
TH = np.load('/work/work/TH_raw.npy')
TH_s = np.load('/work/work/TH_s.npy')
c = 0
# doy 153 -> 0-based row 152; neighbours doy 138..168 -> 0-based 137..167
man = np.mean(TH[137:168, c])
print("manual (137..167):", man, "TH_s[152]:", TH_s[152, c], "match:", np.isclose(man, TH_s[152, c]))
# full-array verification of the circulant mean
off = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
chk = TH[off].mean(axis=1)
print("full recompute matches saved:", np.array_equal(chk, TH_s))
# another spot check with wrap-around: doy 1 (row 0): doy 352..366,1..16 -> 0-based 351..365,0..15
man2 = np.mean(np.concatenate([TH[351:,0], TH[:16,0]]))
print("wrap check doy1:", man2, TH_s[0,0], np.isclose(man2, TH_s[0,0]))
