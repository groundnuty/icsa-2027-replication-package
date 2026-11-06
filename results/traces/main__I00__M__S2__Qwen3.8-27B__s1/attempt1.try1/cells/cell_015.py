import numpy as np, datetime as dt
st = np.load("/tmp/st.npy")
sea = np.load("/tmp/sea.npy")
thr_s = np.load("/tmp/thr_s.npy")
clim_s = np.load("/tmp/clim_s.npy")
doy = np.load("/tmp/doy.npy")
j0, j1 = 4540, 4631
doy_t = doy[j0:j1+1]
T = st[sea]
nsea = T.shape[0]
print("nsea:", nsea)
print("T stats: min %.2f max %.2f mean %.2f" % (T.min(), T.max(), T.mean()))
# per target day: mean SST, mean threshold, fraction hot
base = dt.date(2004,6,1)
for t in range(0, 92, 7):
    d = doy_t[t]
    thr = thr_s[d-1]
    print(base+dt.timedelta(days=t), "doy", d,
          "SST mean %.2f" % T[:,t].mean(),
          "thr mean %.2f" % thr.mean(),
          "frac hot %.4f" % float((T[:,t] >= thr).mean()))
# look at a specific cell trajectory in July 2004 vs baseline July
c = 10
print("\ncell", c, "SST July 2004 (first 10 of July):", T[c, 30:40].round(2))
print("thr doy 182..192 (Jul 1-11) cell:", thr_s[181:192, c].round(3))
# baseline SST for same cell, July of 1992..2002
S = np.load("/tmp/S.npy")
b = sea[c]
print("baseline July 2004-adjacent: Jul 1 2002 SST:", S[sea][c, (dt.date(2002,7,1)-dt.date(1991,12,27)).days].round(2))
print("climatology cell for doy 190:", clim_s[189, c].round(2), " thr:", thr_s[189, c].round(2))
# distribution of T - threshold over all cell-days in July
d = 190
print("doy190: T-thr mean %.3f, max %.3f, frac>0 %.4f" % ((T[:, (dt.date(2004,7,9)-dt.date(2004,6,1)).days]-thr_s[d-1]).mean(),
      (T[:, (dt.date(2004,7,9)-dt.date(2004,6,1)).days]-thr_s[d-1]).max(),
      (T[:, (dt.date(2004,7,9)-dt.date(2004,6,1)).days] >= thr_s[d-1]).mean()))
