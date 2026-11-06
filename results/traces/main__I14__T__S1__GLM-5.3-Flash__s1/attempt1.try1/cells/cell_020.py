import fsspec, xarray as xr, numpy as np, pandas as pd, pickle, warnings

with open('/tmp/stepA.pkl','rb') as fh:
    A = pickle.load(fh)
bdates = A['bdates']; arr_sea = A['arr_sea']
m_start = np.array([1,32,61,92,122,153,183,214,245,275,306,336])
bdoy = m_start[bdates.month.values-1] + bdates.day.values - 1

# 1) brute-force pool dates for a few doys, via calendar arithmetic
def pool_dates_bruteforce(d):
    out = []
    for y in list(range(1991, 2005)):
        for month in range(1, 13):
            import calendar
            for day in range(1, calendar.monthrange(y, month)[1] + 1):
                if not (1992 <= y <= 2002):
                    continue
                dd = m_start[month-1] + day - 1 if not (month == 2 and day == 29) else 60
                # need |offset| <= 5 calendar days between (y,month,day) and a baseline date with doy d
                pass
    return out

# simpler: for each baseline date, window by shifting +/-5 days in real calendar time and map target doy
def pools_by_calendar_shift():
    res = {}
    for d in range(1, 367):
        if d == 60: continue
        cnt = 0
        for t in bdates:
            # the date's own doy
            td = bdoy[list(bdates).index(t)] if False else None
        res[d] = None
    return None

# direct approach: for each date, compute set of target doys d such that date lies within +/-5 calendar days
# of a date with doy d. Equivalent: shift date by k days (k=-5..5) and take its doy as target.
shifted = {}
for k in range(-5, 6):
    sh = bdates + pd.Timedelta(days=k)
    sdoy = m_start[sh.month.values-1] + sh.day.values - 1
    for d_tgt, s in zip(sdoy, sh):
        if d_tgt == 60: continue
        shifted.setdefault(d_tgt, set()).add((s.year, s.month, s.day))

mismatch = 0
for d in [1, 2, 55, 60, 61, 65, 153, 183, 244, 365, 366]:
    # my isin-based membership
    sel = np.isin(bdoy, np.array(sorted({((d + k - 1) % 366) + 1 for k in range(-5, 6)})))
    mine = set(zip(bdates[sel].year, bdates[sel].month, bdates[sel].day))
    if mine != shifted.get(d, set()):
        mismatch += 1
        only_mine = sorted(mine - shifted.get(d, set()))[:4]
        only_shift = sorted(shifted.get(d, set()) - mine)[:4]
        print(f"doy {d}: MISMATCH mine-only {only_mine} shift-only {only_shift} sizes {len(mine)} {len(shifted.get(d,set()))}")
    else:
        print(f"doy {d}: OK ({len(mine)} dates)")
print("pool-date mismatches:", mismatch)

# 2) independent Hazen quantile check on a real pool (doy 153, cell 0)
d = 153
sel = np.isin(bdoy, np.array(sorted({((d + k - 1) % 366) + 1 for k in range(-5, 6)})))
pool = arr_sea[sel][:, 0]
pool = pool[np.isfinite(pool)]
n = len(pool); pos = 0.9*(n+1); lo = int(np.floor(pos)); frac = pos - lo
q_hazen = pool[lo-1] + frac*(pool[lo] - pool[lo-1]) if lo < n else pool[-1]
q_np = np.quantile(pool, 0.9, method='hazen')
print(f"doy153 cell0: n={n} pos={pos:.2f} manual={q_hazen:.6f} numpy={q_np:.6f} match={np.isclose(q_hazen,q_np)}")
# compare against linear-interp conventions for awareness
print("  (linear would be", np.quantile(pool,0.9,method='linear'), "| inverted_cdf", np.quantile(pool,0.9,method='inverted_cdf'), ")")
