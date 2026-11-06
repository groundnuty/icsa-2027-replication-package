
import numpy as np, pickle, datetime as dt, warnings
warnings.filterwarnings("ignore")
dates = pickle.load(open("/work/dates.pkl","rb"))
base_days = dates["baseline_win"]
NC=3600
Sb = np.empty((len(base_days), NC), np.float64)
for i, s in enumerate(base_days):
    Sb[i] = np.load(f"/work/reg/{s}.npy").ravel()
_leap0 = dt.date(2000,1,1)
def doy_of(s):
    y,m,d = map(int, s.split("-"))
    return (dt.date(2000,m,d) - _leap0).days + 1
doyB = np.array([doy_of(s) for s in base_days])
is_baseline = np.array([(s >= "1992-01-01") and (s <= "2002-12-31") for s in base_days])
c = 12345 % 3600
d = 255
idxs = set()
for i, dv in enumerate(doyB):
    if dv == d and is_baseline[i]:
        for k in range(-5,6): idxs.add(i+k)
P = np.sort(np.array(sorted(idxs)))
X = Sb[P, c]
print("pool size:", len(X), "NaNs:", np.isnan(X).sum())
v = X[np.isfinite(X)]
print("n finite:", len(v))
q_np = np.nanquantile(X, 0.9, method="hazen")
def hazen90_manual(vals):
    v = np.sort(vals); n = len(v); h = (n+1)*0.9
    lo = int(np.floor(h)); frac = h-lo
    if lo < 1: return v[0]
    if lo >= n: return v[-1]
    return v[lo-1] + frac*(v[lo]-v[lo-1])
q_man = hazen90_manual(v)
print("numpy nanquantile:", q_np)
print("manual           :", q_man)
print("sorted around rank:", v[105:115])
n = len(v); h1 = (n+1)*0.9
print("h 1-based:", h1)
