import numpy as np, pandas as pd
B = np.load('work/B.npy')
bdates = pd.date_range('1991-12-27', periods=B.shape[0], freq='D')

def sdoy(ts):
    n = ts.day_of_year
    if not ts.is_leap_year and n >= 60: n += 1
    return n
bdoy_s = np.array([sdoy(t) for t in bdates])

def pool_rows(d):
    if d == 60: return None
    rows = set()
    for k in np.where(bdoy_s == d)[0]:
        for off in range(-5, 6):
            q = bdates[k] + pd.Timedelta(days=off)
            rows.add((q - bdates[0]).days)
    return sorted(rows)

# find offending doys
for d in [1, 59, 61, 92, 153, 200, 244, 300, 366]:
    if d == 60: continue
    rows = pool_rows(d)
    bad = [r for r in rows if r < 0 or r >= B.shape[0]]
    if bad:
        print("doy", d, "bad rows:", bad, "-> dates:", [str(bdates[0]+pd.Timedelta(days=int(r))) for r in bad])
        centres = [str(bdates[k].date()) for k in np.where(bdoy_s == d)[0]]
        print("   centres:", centres)
    else:
        print("doy", d, "rows ok:", len(rows), "range", str(bdates[rows[0]].date()), "..", str(bdates[rows[-1]].date()))
