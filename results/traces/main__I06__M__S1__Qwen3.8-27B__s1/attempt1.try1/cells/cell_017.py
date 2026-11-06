import numpy as np, datetime as dt

Z = np.load("/tmp/mhw/loaded.npz")
Vb, Vt = Z["Vb"], Z["Vt"]
BASE_START = dt.date(1991,12,27)
BL_START, BL_END = dt.date(1992,1,1), dt.date(2002,12,31)
leap_month = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
for m in range(1,13):
    s = 1
    for mm in range(1,m): s += leap_month[mm-1]
    for day in range(1, leap_month[m-1]+1):
        doy_of[(m,day)] = s + day - 1

bl_dates = [BL_START + dt.timedelta(days=i) for i in range((BL_END-BL_START).days+1)]
bl_ord = np.array([(dd.toordinal()-BASE_START.toordinal()) for dd in bl_dates])
bl_doy = np.array([doy_of[(dd.month,dd.day)] for dd in bl_dates])
pools = {}
for d in range(1, 367):
    if d == 60: continue
    m = bl_doy == d
    pools[d] = np.unique(bl_ord[m][:,None] + np.arange(-5,6)[None,:])

# verify Feb 29 membership properly
for d in (58,59,60,61,62):
    if d in pools:
        f29 = [(BASE_START+dt.timedelta(days=int(i))).isoformat() for i in pools[d]
               if (BASE_START+dt.timedelta(days=int(i))).month==2 and (BASE_START+dt.timedelta(days=int(i))).day==29]
        print(f"W_{d}: Feb29 dates = {f29}")
print("W_60 exists:", 60 in pools)

# verify hazen manual (HF type 5: 1-based k = n*p + 0.5)
import warnings
warnings.filterwarnings("ignore")
def hazen_manual(v):
    x = np.sort(v[np.isfinite(v)]); n = len(x)
    if n == 0: return np.nan
    k = n*0.9 + 0.5          # 1-based position
    lo1 = int(np.floor(k))   # 1-based index of lower
    if lo1 >= n: return x[-1]
    g = k - lo1
    return x[lo1-1] + (x[lo1]-x[lo1-1])*g if lo1 < n else x[-1]

rng = np.random.default_rng(0)
ok = True
for trial in range(5):
    n = int(rng.integers(1, 300))
    v = rng.normal(285, 3, size=n)
    nm = np.nanquantile(v, 0.9, method="hazen")
    mm = hazen_manual(v)
    if abs(nm-mm) > 1e-9:
        ok = False; print("MISMATCH", n, nm, mm)
print("hazen manual check:", ok)

# verify with real data, cell (10,10), day 172
p = pools[172]
vals = Vb[p, 10, 10]
print("numpy:", np.nanquantile(vals, 0.9, method="hazen"), "manual:", hazen_manual(vals))
