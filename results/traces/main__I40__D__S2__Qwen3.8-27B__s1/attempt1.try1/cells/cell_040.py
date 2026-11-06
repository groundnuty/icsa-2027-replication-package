import numpy as np, datetime
V_base = np.load('/work/V_base.npy').astype(np.float64)
B = V_base.reshape(4028, 3600)
thr_sm = np.load('/work/thr_sm.npy')
hot = np.load('/work/hot.npy'); mask = np.load('/work/mask.npy'); sea = np.load('/work/sea.npy')

d0 = datetime.date(1991,12,27)
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
d = 0
for m in range(1,13):
    for dd in range(1, mdays[m-1]+1):
        d += 1; doy_of[(m,dd)] = d

# manual pool for doy 153 (1 Jun), cell 1000
c = 1000
pool = []
for y in range(1992, 2003):
    b = datetime.date(y, 6, 1)
    assert doy_of[(6,1)] == 153
    for k in range(-5, 6):
        t = b + datetime.timedelta(days=k)
        i = (t - d0).days
        pool.append(B[i, c])
pool = np.array(pool)
print("pool size:", pool.size, "finite:", np.isfinite(pool).sum())
pf = np.sort(pool[np.isfinite(pool)])
n = pf.size
h = 1 + 0.9*(n-1)   # hazen (1-based)
lo_i = int(np.floor(h)); frac = h - lo_i
q_manual = pf[lo_i-1] if frac == 0 else pf[lo_i-1]*(1-frac) + pf[lo_i]*frac
print("manual hazen q90:", q_manual)
# pipeline unsmoothed value: recompute one pool via P for cross-check
# (recompute pool rows from P)
N = 4028
P = np.zeros((N, 367), dtype=bool)
cur = datetime.date(1992,1,1)
while cur <= datetime.date(2002,12,31):
    dd = doy_of[(cur.month, cur.day)]
    if dd != 60:
        k0 = (cur - datetime.timedelta(days=5) - d0).days
        k1 = (cur + datetime.timedelta(days=5) - d0).days
        P[k0:k1+1, dd] = True
    cur += datetime.timedelta(days=1)
rows = np.flatnonzero(P[:, 153])
pool2 = B[rows, c]
print("P-based pool size:", pool2.size, "equal set:", np.array_equal(np.sort(pool2[np.isfinite(pool2)]), pf))
q2 = np.nanquantile(pool2, 0.9, method="hazen")
print("np hazen q90:", q2)

# reconstruct unsmoothed thr col and smoothing at doy 153
thru = np.full(367, np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    thru[dd] = np.nanquantile(B[np.flatnonzero(P[:, dd]), c], 0.9, method="haze n".strip())
thru[60] = 0.5*(thru[59]+thru[61])
idxs = [((153-1)-j) % 366 for j in range(15, -16, -1)]
sm_manual = thru[np.array(idxs)].mean()
print("manual smoothed thr[153, c]:", sm_manual)
print("pipeline thr_sm[153, c]:", thr_sm[153-1, c])
print("match:", np.isclose(sm_manual, thr_sm[153-1, c]))

# merged-run spot check: find a cell with a gap merge
import itertools
found = 0
for c2 in np.flatnonzero(sea):
    h = hot[:, c2]
    prev = np.r_[False, h[:-1]]; nxt = np.r_[h[1:], False]
    s_ = np.flatnonzero(h & ~prev); e_ = np.flatnonzero(h & ~nxt)
    L = e_ - s_ + 1
    if (L >= 5).sum() >= 2:
        gaps = s_[1:] - e_[:-1] - 1
        if np.any((gaps >= 1) & (gaps <= 2)):
            print(f"\ncell {c2}: starts {s_.tolist()} ends {e_.tolist()} gaps {gaps.tolist()}")
            print(" hot :", ''.join('#' if x else '.' for x in h))
            print(" mask:", ''.join('X' if x else '.' for x in mask[:, c2]))
            found += 1
            break
print("found merged example:", found)
