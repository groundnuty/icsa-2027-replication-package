import numpy as np, pandas as pd

# --- correct leap-aligned doy via month/day
CUM_LEAP = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def md_to_doy(month, day):
    return CUM_LEAP[month-1] + day
# cross-check against pandas convention used for the baseline pools
def doy_convention(ts):
    doy = ts.dayofyear.values.copy()
    leap = ts.is_leap_year.values
    after_feb = (ts.month.values > 2)
    return np.where(leap | ~after_feb, doy, doy + 1)

ts = pd.date_range("1999-01-01", "2001-12-31", freq="D")
a = md_to_doy(ts.month.values, ts.day.values)
b = doy_convention(ts)
print("doy mapping agreement over 1999-2001:", bool(np.array_equal(a, b)))
print("Jun1/2005 doy:", md_to_doy(6,1), " Aug31/2005:", md_to_doy(8,31), " Feb29/2000:", md_to_doy(2,29), " Dec31:", md_to_doy(12,31))

# --- synthetic test of run/join logic
def detect(col, minlen=5, gaps=(1,2)):
    nt = col.size
    if not col.any(): return []
    starts = list(np.where((~col[:-1]) & col[1:])[0] + 1)
    if col[0]: starts = [0] + starts
    ends = list(np.where(col[:-1] & (~col[1:]))[0])
    if col[-1]: ends = ends + [nt-1]
    hot_runs = [[s,e] for s,e in zip(starts,ends) if e-s+1 >= minlen]
    merged = []
    for r in hot_runs:
        if merged and (r[0] - merged[-1][1] - 1) in gaps:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged

def mask_from(col, runs):
    m = np.zeros(col.size, bool)
    for s,e in runs: m[s:e+1] = True
    return m

tests = [
    ("5h,2n,5h,1n,3h -> join first two, drop 3-run", [1]*5+[0]*2+[1]*5+[0]+[1]*3+[0]*4, [[0,11]]),
    ("5h,1n,3h -> only first", [1]*5+[0]+[1]*3+[0]*11, [[0,4]]),
    ("5h,2n,5h,2n,5h -> chain all", [1]*5+[0]*2+[1]*5+[0]*2+[1]*5+[0]*2, [[0,18]]),
    ("3h only -> none", [0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], []),
    ("4h,2n,6h -> only 6h", [1]*4+[0]*2+[1]*6+[0]*8, [[6,11]]),
    ("run at both ends", [1]*5+[0]*2+[1]*6+[0]*7, [[0,12]]),
    ("5h,3n,5h -> no join", [1]*5+[0]*3+[1]*5+[0]*4, [[0,4],[8,12]]),
]
for name, col, expect in tests:
    col = np.array(col, bool)
    got = detect(col)
    print(("OK " if got == expect else "FAIL"), name, got)
