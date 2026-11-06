import numpy as np, datetime
V_base = np.load('/work/V_base.npy').astype(np.float64)
B = V_base.reshape(4028, 3600)
thr_sm = np.load('/work/thr_sm.npy'); clim_sm = np.load('/work/clim_sm.npy')
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

import warnings
warnings.simplefilter("ignore")
thru = np.full(367, np.nan); clu = np.full(367, np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    rows = np.flatnonzero(P[:, dd])
    pool = B[rows, 1000]
    thru[dd] = np.nanquantile(pool, 0.9, method="hazen")
    clu[dd] = np.nanmean(pool)
thru[60] = 0.5*(thru[59]+thru[61]); clu[60] = 0.5*(clu[59]+clu[61])

ok = True
for dd_t, c in [(153, 1000), (244, 1000), (1, 1000), (366, 1000), (45, 1000), (60, 1000), (59, 1000), (200, 1000)]:
    w = [(dd_t + j - 1) % 366 + 1 for j in range(-15, 16)]   # doy window
    m_thr = thru[np.array(w)].mean()
    got = thr_sm[dd_t-1, c]
    match = np.isclose(m_thr, got)
    ok &= match
    print(f"doy {dd_t}: manual {m_thr:.9f} pipeline {got:.9f} match {match}")
# climatology check
for dd_t in [153, 244]:
    w = [(dd_t + j - 1) % 366 + 1 for j in range(-15, 16)]
    print(f"clim doy {dd_t}: manual {clu[np.array(w)].mean():.9f} pipeline {clim_sm[dd_t-1, 1000]:.9f} match",
          np.isclose(clu[np.array(w)].mean(), clim_sm[dd_t-1, 1000]))
print("ALL OK:", ok)
# day-60 pool membership sanity: Feb 29 1992 (doy 60) in windows of 59 & 61?
k_29 = (datetime.date(1992,2,29) - d0).days
print("Feb29-1992 in pool59:", bool(P[k_29, 59]), "in pool61:", bool(P[k_29, 61]), "in pool60:", bool(P[k_29, 60]))
# edge windows inside E:
print("1991-12-27 in E rows:", P[0, 1], " (doy1 pool) 2003-01-05:", bool(P[4027, 366]))
