
import numpy as np, datetime as dt
sst_base = np.load('/tmp/sst_base.npy'); bord = np.load('/tmp/bdates.npy')
def doy_of(ordinal):
    d = dt.date.fromordinal(int(ordinal))
    cum = [31,29,31,30,31,30,31,31,30,31,30,31]
    return sum(cum[:d.month-1]) + d.day

# independent pool construction for doy 200 (= July 18) and doy 153 (= June 1)
for d in [200, 153]:
    # find month/day of doy d
    cum = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
    m = int(np.searchsorted(cum, d) + 1)
    day = d - (cum[m-2] if m>1 else 0)
    expected = set()
    for y in range(1992, 2003):
        b = dt.date(y, m, day)
        for k in range(-5, 6):
            expected.add(b.toordinal() + k)
    got = set()
    for i, o in enumerate(bord):
        lo = max(int(o)-5, dt.date(1992,1,1).toordinal()); hi = min(int(o)+5, dt.date(2002,12,31).toordinal())
        for b in range(lo, hi+1):
            if doy_of(b) == d:
                got.add(int(o))
    print("doy", d, "=", m, "/", day, " expected==got:", expected==got, "n:", len(got))

# hand-check hazen quantile for one cell, doy 200
idx200 = []
for i, o in enumerate(bord):
    lo = max(int(o)-5, dt.date(1992,1,1).toordinal()); hi = min(int(o)+5, dt.date(2002,12,31).toordinal())
    for b in range(lo, hi+1):
        if doy_of(b) == 200:
            idx200.append(i)
vals = sst_base[idx200, 1500]
vals = vals[np.isfinite(vals)]
print("n vals:", len(vals))
sv = np.sort(vals)
h = 0.9*len(sv) + 0.5   # hazen: (n+0.5)*p
import math
lo_i = math.floor(h); frac = h - lo_i
q_manual = sv[lo_i-1] + frac*(sv[lo_i]-sv[lo_i-1]) if lo_i < len(sv) else sv[-1]
q_np = np.nanquantile(vals, 0.9, method='hazen')
print("manual:", q_manual, "numpy:", q_np, "match:", np.isclose(q_manual, q_np))
# also compare against other methods to show they differ
print("linear:", np.nanquantile(vals,0.9,method='linear'), "midpoint:", np.nanquantile(vals,0.9,method='midpoint'))
