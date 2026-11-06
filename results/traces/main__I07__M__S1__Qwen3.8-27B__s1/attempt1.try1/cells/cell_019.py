import numpy as np
from datetime import date, timedelta

z = np.load("/tmp/sst_data.npz")
B, T = z["B"], z["T"]; btimes, ttimes = z["btimes"], z["ttimes"]
s2 = np.load("/tmp/step2.npz")
thr, clim, thr_s, sea = s2["thr"], s2["clim"], s2["thr_s"], s2["sea"]

def to_date(ts):
    s = str(ts); return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
base_dates = [to_date(t) for t in btimes]
loaded = {d: i for i, d in enumerate(base_dates)}
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return cum[d.month-1] + d.day

sea_idx = np.where(sea.ravel())[0]
Bflat = B.reshape(len(base_dates), 3600)

def pool_plain(d0, cell):
    # all loaded dates t within +-5 cal days of a baseline date b with doy(b)=d0+1
    vals = []
    for b in base_dates:
        if not (date(1992,1,1) <= b <= date(2002,12,31)): continue
        if doy(b) != d0 + 1: continue
        for k in range(-5, 6):
            t = b + timedelta(days=k)
            vals.append(Bflat[loaded[t], cell])
    return np.array(vals, dtype=np.float64)

# pick 3 sea cells, 3 doys incl. 59,60,61 and 366
tests = [(sea_idx[0], 0), (sea_idx[100], 60), (sea_idx[100], 58), (sea_idx[100], 59),
         (sea_idx[100], 60), (sea_idx[100], 365), (sea_idx[2000], 182)]
for cell, d0 in tests:
    v = pool_plain(d0, cell)
    v = v[~np.isnan(v)]
    q = np.quantile(v, 0.9, method="hazen")
    m = v.mean()
    # stored: row index in ncell ordering
    c = int(np.searchsorted(sea_idx, cell))
    ok_t = np.isclose(q, thr[c, d0]) if d0 != 59 else np.isclose((thr[c,58]+thr[c,60])/2, thr[c,59])
    ok_c = np.isclose(m, clim[c, d0]) if d0 != 59 else np.isclose((clim[c,58]+clim[c,60])/2, clim[c,59])
    print(f"cell {cell} doy {d0+1}: n={v.size} plain q={q:.6f} stored={thr[c,d0]:.6f} match={ok_t} | plain mean={m:.6f} stored={clim[c,d0]:.6f} match={ok_c}")

# independent smoothing check (explicit loop, wrap-around) for one cell
c = 5
a = thr[c]
sm = np.array([a[(i + k) % 366].mean() for i in range(366) for k in range(-15, 16)][:366] if False else
              [np.mean([a[(i + k) % 366] for k in range(-15, 16)]) for i in range(366)])
print("smoothing check max diff:", np.abs(sm - thr_s[c]).max())

# check Feb-29 (doy 60) values contribute to neighbours: pool of doy 61 should include 29 Feb values
v61 = pool_plain(60, sea_idx[100])
print("doy61 pool size:", v61.size, "(expect 121; includes 29Feb values from leap years)")
