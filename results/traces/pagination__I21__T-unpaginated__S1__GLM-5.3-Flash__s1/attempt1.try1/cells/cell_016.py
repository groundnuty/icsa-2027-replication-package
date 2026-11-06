import numpy as np, datetime as dt, pickle, json

# ---- assemble baseline cube: dates 1991-12-27 .. 2003-01-05 (4028 days) ----
d0, d1 = dt.date(1991,12,27), dt.date(2003,1,5)
bdates = [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]
assert len(bdates) == 4028
parts = []
for ci in range(4):
    parts.append(np.load(f'/tmp/region_chunk{ci}.npy'))
tail = np.load('/tmp/region_chunk4.npy')[:28]   # 2002-12-09 .. 2003-01-05
parts.append(tail)
base = np.concatenate(parts, axis=0).astype(np.float64)
assert base.shape == (4028, 60, 60), base.shape
# date alignment sanity: finite counts per chunk
for ci in range(4):
    with open(f'/tmp/region_meta{ci}.pkl','rb') as f: m = pickle.load(f)
    print("chunk", ci, m['start'], m['end'], m['n'])
print("baseline cube:", base.shape, "finite:", int(np.isfinite(base).sum()))

# ---- sea cells: finite on every target day ----
tgt = np.load('/tmp/target_region.npy').astype(np.float64)
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
assert tgt.shape[0] == 92
fin_t = np.isfinite(tgt)
sea = fin_t.all(axis=0)
print("sea cells:", int(sea.sum()), "of", sea.size)
# baseline finiteness on sea cells (diagnostic)
fin_b = np.isfinite(base)
print("baseline finite frac on sea cells: min %.6f max %.6f" % (
    fin_b[:,sea].mean(axis=0).min(), fin_b[:,sea].mean(axis=0).max()))
# every cell with some baseline data must be a sea cell?
print("cells with baseline data but not sea:", int(((fin_b.any(axis=0)) & (~sea)).sum()))
print("sea cells missing all baseline data:", int((sea & (~fin_b.any(axis=0))).sum()))
np.save('/tmp/base_cube.npy', base); np.save('/tmp/tgt_cube.npy', tgt)

# ---- pool index for doy 1..366 (skip 60) ----
bdoy = np.array([mapped_doy(d) if False else (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1 for d in bdates])
bidx = {d: i for i, d in enumerate(bdates)}
pools = {}
for doy in range(1, 367):
    if doy == 60: continue
    idxs = []
    for year in range(1992, 2003):
        try:
            anchor = dt.date(year, 2, 29) if (doy == 60 and False) else None
        except ValueError:
            anchor = None
    # anchor date for this doy in this year (skip Feb 29 anchors entirely)
    for year in range(1992, 2003):
        # construct anchor from doy in a leap frame, but only for doy != 60
        leap_anchor = dt.date(2000,1,1) + dt.timedelta(days=doy-1)
        if leap_anchor.month == 2 and leap_anchor.day == 29:
            continue  # no anchor for Feb 29
        try:
            anchor = dt.date(year, leap_anchor.month, leap_anchor.day)
        except ValueError:
            continue  # e.g. Feb 29 anchor in non-leap year -> skip
        aidx = bidx[anchor]
        for off in range(-5, 6):
            j = aidx + off
            if 0 <= j < len(bdates):
                idxs.append(j)
    pools[doy] = np.array(sorted(set(idxs)))
lens = np.array([len(v) for v in pools.values()])
print("pool lengths: min", lens.min(), "max", lens.max(), "mean %.1f" % lens.mean())
print("doy 1 pool:", len(pools[1]), "doy 59:", len(pools[59]), "doy 61:", len(pools[61]), "doy 366:", len(pools[366]))
print("doy 1 window:", bdates[pools[1][0]], "..", bdates[pools[1][-1]])
print("doy 366 window:", bdates[pools[366][0]], "..", bdates[pools[366][-1]])
# verify every baseline date used somewhere
used = np.zeros(len(bdates), bool)
for v in pools.values(): used[v] = True
print("baseline days used:", int(used.sum()), "of", len(bdates), "| unused (should be Feb29s=3):", int((~used).sum()))
unused_dates = [bdates[i].isoformat() for i in np.where(~used)[0]]
print("unused:", unused_dates)
with open('/tmp/pools.pkl','wb') as f: pickle.dump(pools, f)
