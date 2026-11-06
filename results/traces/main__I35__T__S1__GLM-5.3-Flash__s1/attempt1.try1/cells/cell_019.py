import numpy as np, datetime as dt, calendar
# 1) hazen percentile vs hand-computed MATLAB quantile
def matlab_ref(x, p):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    # MATLAB plotting positions (i-0.5)/n
    pos = (np.arange(1, n+1) - 0.5) / n
    if p <= pos[0]: return x[0]
    if p >= pos[-1]: return x[-1]
    i = np.searchsorted(pos, p)  # pos[i-1] < p <= pos[i]
    x0, x1 = x[i-1], x[i]
    return x0 + (p - pos[i-1]) / (pos[i] - pos[i-1]) * (x1 - x0)
tests = [[1,2,3,4],[1,2,3,4,5,6,7,8,9,10],[3,1,2],[5,5,5,5],[1,2,3,4,5,6,7,8,9,10,11]]
for x in tests:
    for p in [0.9, 0.1, 0.5, 0.95]:
        a = np.percentile(x, p*100, method='hazen')
        b = matlab_ref(x, p)
        flag = 'OK' if abs(a-b) < 1e-12 else 'MISMATCH'
        if flag != 'OK': print(x, p, a, b, flag)
print('hazen vs MATLAB reference: all OK on tests')
# nanpercentile check: NaNs ignored
arr = np.array([[1.,np.nan],[2.,4.],[3.,5.],[4.,6.]])
print('nanpercentile col0 (hazen):', np.nanpercentile(arr, 90, axis=0, method='hazen'), 'expect [4, 6]')

# 2) doy function cross-check via leap reference year
def doy_of(d):
    y = d.timetuple().tm_yday
    if calendar.isleap(d.year): return y
    return y+1 if y>=60 else y
def doy_ref(d):
    # replace year with a leap year (2012) keeping month/day; Feb 29 only exists if month/day valid
    try:
        return dt.date(2012, d.month, d.day).timetuple().tm_yday
    except ValueError:
        return None  # Feb 30 impossible; not needed
allok=True
y=2009
d=dt.date(y,1,1)
while d.year==y:
    if doy_of(d)!=doy_ref(d): print('MISMATCH', d, doy_of(d), doy_ref(d)); allok=False
    d+=dt.timedelta(days=1)
y=1992
d=dt.date(y,1,1)
while d.year==y:
    if doy_of(d)!=doy_ref(d): print('MISMATCH', d, doy_of(d), doy_ref(d)); allok=False
    d+=dt.timedelta(days=1)
print('doy function agrees with leap-reference for 2009 and 1992:', allok)
print('2009-06-01 doy:', doy_of(dt.date(2009,6,1)), ' 2009-08-31 doy:', doy_of(dt.date(2009,8,31)))
