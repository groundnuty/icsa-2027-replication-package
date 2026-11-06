import numpy as np, datetime as dt

# --- Test 1: hazen percentile (type 5) vs manual formula ---
rng = np.random.default_rng(42)
for n in [7, 121, 50]:
    x = np.sort(rng.normal(size=n))
    p = 0.9
    h = p*n + 0.5           # Hyndman-Fan type 5 (hazen): h = n*p + 1/2, 1-based
    i = int(np.floor(h))
    q_manual = x[i-1] + (h - i)*(x[i] - x[i-1]) if i < n else x[-1]
    q_np = np.percentile(x, 90, method="hazen")
    print(f"n={n}: manual={q_manual:.10f} numpy hazen={q_np:.10f} equal={np.isclose(q_manual,q_np,rtol=0,atol=1e-12)}")

# NaN handling equivalence
x = rng.normal(size=121); x[[3,10,50]] = np.nan
qn = np.nanpercentile(x, 90, method="hazen")
qm = np.percentile(x[np.isfinite(x)], 90, method="hazen")
print("nan handling equal:", np.isclose(qn, qm, rtol=0, atol=1e-12))

# --- Test 2: circular 31-day moving mean vs naive loop ---
arr = rng.normal(size=366)
pad = np.concatenate([arr[-15:], arr, arr[:15]])
c = np.concatenate([[0.0], np.cumsum(pad)])
out = (c[31:31+366] - c[0:366]) / 31.0
naive = np.array([np.mean([arr[(i+o) % 366] for o in range(-15,16)]) for i in range(366)])
print("circular smoothing max abs diff:", np.abs(out - naive).max())

# --- Test 3: leap-style day-of-year mapping ---
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def leap_doy(d):
    return CUM[d.month-1] + d.day
tests = {(2000,1,1):1,(1999,2,28):59,(2000,2,28):59,(2000,2,29):60,(1999,3,1):61,
         (2000,3,1):61,(2015,6,1):153,(2015,8,31):244,(2000,12,31):366,(1992,2,29):60}
for (y,m,dd), exp in tests.items():
    got = leap_doy(dt.date(y,m,dd))
    print(f"{y}-{m:02d}-{dd:02d} -> {got} (expect {exp}) {'OK' if got==exp else 'FAIL'}")
# 2015 non-leap: no day 60; check Jun1=153..Aug31=244 range
print("2015-06-01..2015-08-31 doys:", leap_doy(dt.date(2015,6,1)), "..", leap_doy(dt.date(2015,8,31)))
