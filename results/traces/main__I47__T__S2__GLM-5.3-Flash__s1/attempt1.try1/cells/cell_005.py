import numpy as np, datetime as dt
from numpy.lib.stride_tricks import sliding_window_view
from collections import defaultdict

# ---------- 1. day-of-year mapping (leap-aligned: same mdoy in every year) ----------
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # leap-aligned cumulative
def mdoy(date): return int(CUM[date.month-1]) + date.day
def mdoy_vec(dates):
    months = dates.astype('datetime64[M]').astype(int) % 12 + 1
    days = (dates - dates.astype('datetime64[M]')).astype('timedelta64[D]').astype(int) + 1
    return CUM[months-1] + days

cases = {'1991-12-27':362,'1991-12-31':366,'1992-01-01':1,'1992-02-28':59,'1992-02-29':60,
         '1992-03-01':61,'1993-02-28':59,'1993-03-01':61,'1993-12-31':366,'1996-12-31':366,
         '2000-02-29':60,'2019-02-28':59,'2019-03-01':61,'2019-06-01':153,'2019-08-31':244,
         '2002-12-31':366,'1992-12-31':366,'1993-02-27':58,'1993-03-02':62,'2000-03-01':61,
         '2019-08-01':214,'1992-06-30':182,'1993-07-01':183}
for s,v in cases.items():
    y,m,d = map(int, s.split('-'))
    got = mdoy(dt.date(y,m,d))
    assert got == v, (s, got, v)
dts = np.array(sorted(cases.keys()), dtype='datetime64[D]')
assert list(mdoy_vec(dts)) == [cases[str(x)] for x in dts]
# cross-check against python calendar for a leap and non-leap year
import calendar
for y in (1992, 1993, 2000, 2019):
    d0 = dt.date(y,1,1); d1 = dt.date(y,12,31)
    ndays = (d1-d0).days + 1
    vals = [mdoy(d0+dt.timedelta(days=k)) for k in range(ndays)]
    if calendar.isleap(y):
        assert vals == list(range(1,367)), y
    else:
        exp = list(range(1,60)) + list(range(61,367))  # no day 60
        assert vals == exp, y
print("doy mapping OK (leap-aligned, all years)")

# ---------- 2. Hazen (type 5) quantile, NaN-aware, column-wise ----------
rng = np.random.default_rng(42)
k, ncol = 121, 3600
P = rng.normal(size=(k, ncol)); P[rng.random(P.shape) < 0.35] = np.nan; P[:, :10] = np.nan
s = np.sort(P, axis=0)
n = np.count_nonzero(~np.isnan(P), axis=0)
pos = 0.9*(n-1)
lo0 = np.floor(pos).astype(np.int64); frac = pos - lo0
hi0 = np.minimum(lo0+1, n-1); cols = np.arange(ncol)
q = s[lo0, cols] + frac*(s[hi0, cols] - s[lo0, cols]); q[n == 0] = np.nan
try:
    ref = np.nanquantile(P, 0.9, axis=0, method='hazen')
    print("hazen max|diff| vs numpy method='hazen':", np.nanmax(np.abs(q-ref)),
          "| NaN pattern match:", np.array_equal(np.isnan(q), np.isnan(ref)))
except TypeError as e:
    print("no method= in numpy:", e)
for c in (15, 777, 3599):
    x = np.sort(P[~np.isnan(P[:,c]), c]); nn = len(x)
    h = 0.9*(nn-1)+1; lf = int(np.floor(h)); site_g = h-lf
    val = x[lf-1] if site_g == 0 else x[lf-1] + site_g*(x[lf]-x[lf-1])
    print(f"  col {c}: manual {val:.12f} vs ours {q[c]:.12f} match {abs(val-q[c])<1e-12}")

# ---------- 3. circular 31-day centred moving mean ----------
arr = rng.normal(size=366)
padded = np.concatenate([arr[-15:], arr, arr[:15]])
sm = sliding_window_view(padded, 31).mean(axis=1)
ref = np.array([arr[(np.arange(d-15, d+16)) % 366].mean() for d in range(1, 367)])
print("smoothing max|diff|:", np.abs(sm-ref).max())

# ---------- 4. run detection (>=5) + join gaps <=2 ----------
def ref_cell_mhw(hot):
    T = len(hot); ivals = []; i = 0
    while i < T:
        if hot[i]:
            j = i
            while j+1 < T and hot[j+1]: j += 1
            ivals.append([i, j]); i = j+1
        else: i += 1
    ivals = [iv for iv in ivals if iv[1]-iv[0]+1 >= 5]
    merged = []
    for a, b in ivals:
        if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
        else: merged.append([a, b])
    out = np.zeros(T, bool)
    for a, b in merged: out[a:b+1] = True
    return out

def vec_mhw(hot):
    T, N = hot.shape
    z = np.zeros((T+2, N), np.int8); z[1:-1] = hot
    dz = z[1:] - z[:-1]
    out = np.zeros((T, N), bool)
    for c in range(N):
        col = dz[:, c]
        ss = list(np.nonzero(col == 1)[0]); ee = list(np.nonzero(col == -1)[0])
        assert len(ss) == len(ee)
        ivals = [[a, b-1] for a, b in zip(ss, ee)]
        ivals = [iv for iv in ivals if iv[1]-iv[0]+1 >= 5]
        merged = []
        for a, b in ivals:
            if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
            else: merged.append([a, b])
        for a, b in merged: out[a:b+1, c] = True
    return out

T = 92
craft = np.zeros((T, 8), bool)
craft[0:5, 0] = True
craft[87:92, 1] = True
craft[0:5, 2] = True; craft[7:9, 2] = True; craft[11:21, 2] = True
craft[10:14, 3] = True
craft[10:15, 4] = True; craft[18:23, 4] = True
craft[10:15, 5] = True; craft[16:22, 5] = True
craft[10:14, 6] = True; craft[15:20, 6] = True
craft[30:35, 7] = True; craft[38:44, 7] = True; craft[47:52, 7] = True
got = vec_mhw(craft)
exp = np.stack([ref_cell_mhw(craft[:, c]) for c in range(8)], axis=1)
print("crafted cases match:", np.array_equal(got, exp))
for p in (0.3, 0.55, 0.7):
    rand = rng.random((92, 500)) < p
    print(f"random p={p} match:", np.array_equal(vec_mhw(rand),
          np.stack([ref_cell_mhw(rand[:, c]) for c in range(500)], axis=1)))
print("ALL VERIFICATION PASSED")
