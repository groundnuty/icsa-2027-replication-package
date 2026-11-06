
import pandas as pd
times = pd.DatetimeIndex(sub.time.values)
vals = sub.values.astype(np.float64)  # (T, 60, 60)
def doy_of(t):
    # month/day based: 29 Feb=60, Dec31=366, and Jan1=1 etc.
    if t.month==2 and t.day==29: return 60
    cum=[0,31,59,90,120,151,181,212,243,273,304,334]  # non-leap cumulative
    d=cum[t.month-1]+t.day
    if t.month>2: d+=0  # Feb29 handled; in non-leap years Mar1=60 -> must be 61
    return d if (t.month<=2) else d+1
# check mapping: Mar1 -> 61, Dec31 -> 366
print(doy_of(pd.Timestamp('2001-03-01')), doy_of(pd.Timestamp('2001-12-31')), doy_of(pd.Timestamp('2001-02-28')), doy_of(pd.Timestamp('2000-02-29')))
tidx = {t:i for i,t in enumerate(times)}
base = pd.date_range('1992-01-01','2002-12-31')
pools = {d:[] for d in range(1,367) if d!=60}
for b in base:
    d = doy_of(b)
    if d==60: continue
    for k in range(-5,6):
        t = b+pd.Timedelta(days=k)
        pools[d].append(tidx[t])   # idx into times
print(times[0], times[-1], len(times))
# check the window coverage
print(times[tidx[pd.Timestamp('1992-01-01')-pd.Timedelta(days=5)]])
