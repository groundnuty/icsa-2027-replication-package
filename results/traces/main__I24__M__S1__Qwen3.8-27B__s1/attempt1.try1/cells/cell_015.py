import numpy as np, datetime as dt, collections, pickle

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mcum = [0] + list(np.cumsum(mlen))
def doy(d):
    return mcum[d.month-1] + d.day

checks = [(dt.date(2004,1,1),1), (dt.date(2003,1,1),1), (dt.date(2004,2,28),59), (dt.date(2004,2,29),60),
          (dt.date(2003,2,28),59), (dt.date(2003,3,1),61), (dt.date(2004,3,1),61), (dt.date(2003,7,4),186),
          (dt.date(2004,7,4),186), (dt.date(2003,7,3),185), (dt.date(2004,12,31),366), (dt.date(2003,12,31),366),
          (dt.date(2003,2,27),58), (dt.date(2003,1,31),31)]
for d, exp in checks:
    got = doy(d)
    assert got == exp, (d, got, exp)
print("doy checks ok")

start = dt.date(1991,12,27); end = dt.date(2003,1,5)
nb = (end - start).days + 1
print("n baseline-period days:", nb)
ts = dt.date(2004,6,1); te = dt.date(2004,8,31)
nt = (te - ts).days + 1
print("n target days:", nt, "target doy range:", doy(ts), doy(te))

idx_of = {}
dates = [start + dt.timedelta(days=k) for k in range(nb)]
for k, d in enumerate(dates):
    idx_of[d] = k

pools = collections.defaultdict(list)
n_anchors = n_skip60 = 0
for d in dates:
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        dd = doy(d)
        n_anchors += 1
        if dd == 60:
            n_skip60 += 1
            continue
        for k in range(-5, 6):
            t = d + dt.timedelta(days=k)
            assert t in idx_of, t
            pools[dd].append(idx_of[t])

print("anchors:", n_anchors, "skipped doy60:", n_skip60)
sizes = {d: len(v) for d, v in pools.items()}
print("n pools:", len(pools), "size min/max:", min(sizes.values()), max(sizes.values()))
odd = {d: s for d, s in sizes.items() if s != 121}
print("non-121 sizes:", odd)
print("dups within pools:", sum(len(v) - len(set(v)) for v in pools.values()))
print("60 in pools?", 60 in pools, "| 59:", sizes[59], "61:", sizes[61])

# save pools for later (pickle)
pool_arrays = {d: np.asarray(v, dtype=np.int32) for d, v in pools.items()}
with open("/tmp/pools.pkl", "wb") as f:
    pickle.dump(pool_arrays, f)
print("saved /tmp/pools.pkl")
