import numpy as np, datetime as dt

# Rebuild pool index sets with the CORRECT rule: for doy d (!=60), pool dates = union over baseline
# dates b with doy(b)==d of the 11 calendar dates b-5..b+5 (calendar days; windows may extend
# beyond 1992-01-01..2002-12-31 into 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05).
def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n

d0 = dt.date(1982,1,1)
bstart = (dt.date(1991,12,27) - d0).days   # B[0] corresponds to this date
baseline = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range(11*365+3)]  # 1992..2002 inclusive
assert baseline[0]==dt.date(1992,1,1) and baseline[-1]==dt.date(2002,12,31), (baseline[0], baseline[-1])
print("n baseline years dates:", len(baseline))
bdoy = np.array([doy_of(b) for b in baseline])

pool_by_doy = {}
for d in range(1, 367):
    if d == 60:
        pool_by_doy[d] = None
        continue
    centers = [b for b in baseline if doy_of(b) == d]
    idxs = set()
    for c in centers:
        ci = (c - d0).days
        idxs.update(range(ci-5, ci+6))
    pool_by_doy[d] = np.array(sorted(idxs), dtype=np.int64) - bstart  # rows into B

# validations
sizes = {d: (len(v) if v is not None else 0) for d, v in pool_by_doy.items()}
sz = np.array([sizes[d] for d in range(1,367)])
print("pool sizes: min", sz[sz>0].min(), "max", sz.max(), "| n doys with pool:", (sz>0).sum(), "| doy60 size:", sizes[60])
assert np.all(sz[sz>0] == 121)
# doy 1: check range
i1 = pool_by_doy[1]
print("doy1 date range:", dt.date(1991,12,27)+dt.timedelta(days=int(i1.min())), "..", dt.date(1991,12,27)+dt.timedelta(days=int(i1.max())))
# doy 366
i366 = pool_by_doy[366]
print("doy366 date range:", dt.date(1991,12,27)+dt.timedelta(days=int(i366.min())), "..", dt.date(1991,12,27)+dt.timedelta(days=int(i366.max())))
# doy 59 and 61 must both include 1992-02-29 etc. (leap-day values belong to neighbours' windows)
for d in [58, 59, 61, 62]:
    idxs = pool_by_doy[d]
    dates = [dt.date(1991,12,27)+dt.timedelta(days=int(i)) for i in idxs]
    has_leapdays = [x for x in dates if (x.month==2 and x.day==29)]
    print(f"doy {d}: n={len(idxs)}, range {dates[0]}..{dates[-1]}, leap-day dates: {len(has_leapdays)}", has_leapdays[:3])
# verify doy 61 window around 1993-03-01: includes 1993-02-24 (doy 55 of 1993)
idxs61 = pool_by_doy[61]
dates61 = set(dt.date(1991,12,27)+dt.timedelta(days=int(i)) for i in idxs61)
print("doy61 includes 1993-02-24:", dt.date(1993,2,24) in dates61, "| includes 1993-03-06:", dt.date(1993,3,6) in dates61)
print("doy61 includes 1993-02-23:", dt.date(1993,2,23) in dates61, "| includes 1993-03-07:", dt.date(1993,3,7) in dates61)
# doy 1 window around 1992-01-01 includes 1991-12-27..31 and 1992-01-01..06
dates1 = set(dt.date(1991,12,27)+dt.timedelta(days=int(i)) for i in pool_by_doy[1])
print("doy1 includes 1991-12-27..31:", all(dt.date(1991,12,x) in dates1 for x in range(27,32)))
print("doy1 includes 1992-01-01..06:", all(dt.date(1992,1,x) in dates1 for x in range(1,7)))
# sanity: all indices within B bounds
allidx = np.concatenate([v for v in pool_by_doy.values() if v is not None])
print("pool idx range in B rows:", allidx.min(), allidx.max(), "| B rows:", B.shape if False else 4028)
np.save('work/pool_sizes_check.npy', sz)
import pickle
with open('work/pools.pkl','wb') as f_:
    pickle.dump({k: v for k, v in pool_by_doy.items()}, f_)
print("pools saved.")
