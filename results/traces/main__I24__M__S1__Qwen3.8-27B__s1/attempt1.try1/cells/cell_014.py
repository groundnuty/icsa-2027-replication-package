import numpy as np, datetime as dt

# day-of-year mapping: fixed leap-year calendar (month,day) -> 1..366, 29 Feb = 60
def doy_of(d):  # d: datetime.date
    cum = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
    return int(np.searchsorted(cum, d.day + (d.month-1) and 0) ) if False else None

# simpler: table
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mcum = [0] + list(np.cumsum(mlen))
def doy(d):
    return mcum[d.month-1] + d.day

checks = [(dt.date(2004,1,1),1), (dt.date(2003,1,1),1), (dt.date(2004,2,28),59), (dt.date(2004,2,29),60),
          (dt.date(2003,2,28),59), (dt.date(2003,3,1),60), (dt.date(2004,3,1),61), (dt.date(2003,7,4),185),
          (dt.date(2004,7,4),186), (dt.date(2004,12,31),366), (dt.date(2003,12,31),365), (dt.date(2003,2,27),58)]
for d, exp in checks:
    got = doy(d)
    assert got == exp, (d, got, exp)
print("doy checks ok")

# build baseline + extension date array
start = dt.date(1991,12,27)
end = dt.date(2003,1,5)
nb = (end - start).days + 1
print("n baseline-period days:", nb)  # expect 4028

# target
ts = dt.date(2004,6,1); te = dt.date(2004,8,31)
nt = (te - ts).days + 1
print("n target days:", nt)  # 92
print("target doy range:", doy(ts), doy(te))

# pool construction
idx_of = {}
dates = [start + dt.timedelta(days=k) for k in range(nb)]
for k, d in enumerate(dates):
    idx_of[d] = k

import collections
pools = collections.defaultdict(list)
n_anchors = 0
n_skipped_60 = 0
for d in dates:
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        dd = doy(d)
        n_anchors += 1
        if dd == 60:
            n_skipped_60 += 1
            continue
        for k in range(-5, 6):
            t = d + dt.timedelta(days=k)
            assert t in idx_of, t  # must be within our array
            pools[dd].append(idx_of[t])

print("anchors:", n_anchors, "skipped doy60 anchors:", n_skipped_60)
sizes = {d: len(v) for d, v in pools.items()}
print("n pools:", len(pools), "size min/max:", min(sizes.values()), max(sizes.values()))
import itertools
odd = {d: s for d, s in sizes.items() if s not in (121,)}
print("non-121 sizes:", odd)
# check no duplicates within a pool
dups = sum(len(v) - len(set(v)) for v in pools.values())
print("dups within pools:", dups)
np.save("/tmp/pool_test.npy", np.array([[d, len(v)] for d, v in sorted(pools.items())]))
print("doy 59 size, 60 in pools?", 60 in pools, "59:", len(pools[59]), "61:", len(pools[61]))
