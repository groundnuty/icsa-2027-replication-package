import numpy as np, datetime as dt
print("numpy", np.__version__)
import xarray as xr
print("xarray", xr.__version__)

# doy mapping (A): leap-style cumulative by (month, day); Feb29=60; Dec31=366 in every year
CUM = [31,29,31,30,31,30,31,31,30,31,30,31]  # cumulative through month
def dayofyear(d: dt.date) -> int:
    return sum(CUM[:d.month-1]) + d.day
def doy_to_monthday(doy: int):
    m = 0
    for i, c in enumerate(CUM):
        if doy <= c:
            return i+1, doy - (sum(CUM[:i]) if i else 0)
        doy -= c if False else 0
    raise ValueError
# simpler
def doy_to_monthday(doy):
    cum = 0
    for m in range(1, 13):
        c = CUM[m-1]
        if doy <= cum + c:
            return m, doy - cum
        cum += c
    raise ValueError(doy)

tests = [(dt.date(1992,1,1),1),(dt.date(1992,2,28),59),(dt.date(1992,2,29),60),(dt.date(1992,3,1),61),
         (dt.date(1993,2,28),59),(dt.date(1993,3,1),61),(dt.date(1993,12,31),366),(dt.date(2000,2,29),60),
         (dt.date(2002,12,31),366),(dt.date(2012,6,1),153),(dt.date(2012,8,31),244),(dt.date(1996,12,31),366)]
for d, e in tests:
    g = dayofyear(d)
    assert g == e, (d, g, e)
    m, dd = doy_to_monthday(g)
    if not (m == 2 and dd == 29 and d.year not in (1992,1996,2000,2004,2008,2012)):
        assert (m, dd) == (d.month, d.day), (d, m, dd)
print("doy mapping round-trip OK")
print("doy 60 ->", doy_to_monthday(60), "| doy 366 ->", doy_to_monthday(366), "| doy 59 ->", doy_to_monthday(59), "| doy 61 ->", doy_to_monthday(61))

# check hazen support
rng = np.random.default_rng(0)
a = rng.random(100)
q1 = np.quantile(a, 0.9, method='hazen')
print("hazen quantile ok:", q1)
q2 = np.nanpercentile(np.where(rng.random(100)<0.1, np.nan, a), 90, method='hazen')
print("nanpercentile hazen ok:", q2)
