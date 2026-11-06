import numpy as np, datetime
# 1) confirm numpy hazen == HF type 5: h = n*p + 0.5 (1-based interpolation position)
a5 = np.arange(1, 6, dtype=float)
print("n=5 p=0.9:", np.quantile(a5, 0.9, method="hazen"), "(expect 5.0, h=4.5+0.5=5.0)")
a10 = np.arange(1, 11, dtype=float)
print("n=10 p=0.9:", np.quantile(a10, 0.9, method="hazen"), "(expect 9.5, h=9+0.5=9.5)")
a4 = np.arange(1, 5, dtype=float)
print("n=4 p=0.9:", np.quantile(a4, 0.9, method="hazen"), "(expect 3.7, h=3.6+0.5=4.1 -> x[3.1]? check: h=4*0.9+0.5=4.1 -> between 4th (4) ... wait)")

# 2) redo audit of smoothed threshold for cell 1000, doy 153, using np hazen
V_base = np.load('/work/V_base.npy').astype(np.float64)
B = V_base.reshape(4028, 3600)
thr_sm = np.load('/work/thr_sm.npy')
d0 = datetime.date(1991,12,27)
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
d = 0
for m in range(1,13):
    for dd in range(1, mdays[m-1]+1):
        d += 1; doy_of[(m,dd)] = d
P = np.zeros((4028, 367), dtype=bool)
cur = datetime.date(1992,1,1)
while cur <= datetime.date(2002,12,31):
    dd = doy_of[(cur.month, cur.day)]
    if dd != 60:
        k0 = (cur - datetime.timedelta(days=5) - d0).days
        k1 = (cur + datetime.timedelta(days=5) - d0).days
        P[k0:k1+1, dd] = True
    cur += datetime.timedelta(days=1)
c = 1000
thru = np.full(367, np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    thru[dd] = np.nanquantile(B[np.flatnonzero(P[:, dd]), c], 0.9, method="hazen")
thru[60] = 0.5*(thru[59]+thru[61])
idxs = np.array([((153-1)-j) % 366 for j in range(15, -16, -1)])
sm_manual = thru[idxs].mean()
print("manual smoothed thr[153,1000]:", sm_manual, " pipeline:", thr_sm[152, c], " match:", np.isclose(sm_manual, thr_sm[152, c]))
# also for doy 244 and a random cell
for dd_t, c2 in [(244, 500), (138, 3000)]:
    idxs2 = np.array([((dd_t-1)-j) % 366 for j in range(15, -16, -1)])
    thru2 = np.full(367, np.nan)
    for dd in range(1, 367):
        if dd == 60: continue
        thru2[dd] = np.nanquantile(B[np.flatnonzero(P[:, dd]), c2], 0.9, method="hazen")
    thru2[60] = 0.5*(thru2[59]+thru2[61])
    print(dd_t, c2, np.isclose(thru2[idxs2].mean(), thr_sm[dd_t-1, c2]))
