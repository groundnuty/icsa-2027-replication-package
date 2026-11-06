import numpy as np

def mhw_runs(h):
    """vectorized-ish: returns list of merged MHW (start,end) inclusive for bool array h"""
    nd = len(h)
    diff = np.diff(h.astype(np.int8))
    starts = list(np.where(diff == 1)[0] + 1)
    if h[0]: starts.insert(0, 0)
    ends = list(np.where(diff == -1)[0])
    if h[-1]: ends.append(nd - 1)
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged

def brute_mask(h):
    """independent: day t is in MHW if belongs to a maximal merged cluster:
    cluster = connected component of hot days under distance <=3 (i.e., gap <=2)
    where the component contains >=5 hot days... CAREFUL: rule is runs of >=5 hot days,
    then merge. Brute force per spec: mark day t if it is in a run of >=5 consecutive hot days,
    OR it is a gap day (<=2 long) between two such runs (transitively)."""
    nd = len(h)
    is_run_day = np.zeros(nd, bool)
    t = 0
    while t < nd:
        if h[t]:
            u = t
            while u + 1 < nd and h[u+1]:
                u += 1
            if u - t + 1 >= 5:
                is_run_day[t:u+1] = True
            t = u + 1
        else:
            t += 1
    # transitive closure over gap-<=2 between run days
    mask = is_run_day.copy()
    changed = True
    while changed:
        changed = False
        for t in range(nd):
            if is_run_day[t] and not mask[t]:
                # t is a run day, check if connectable to existing mask via gap<=2 chain
                # simpler: iterative: if mask[t] and there's run day within <=2 non-hot days... 
                pass
    # do it properly with BFS over (run days + their gap neighbourhood)
    import collections
    # components of hot days under gap<=2
    comp = -np.ones(nd, int)
    cid = 0
    # build graph on hot day indices: edge if distance-1 (gap) <= 2
    hot_idx = np.where(h)[0]
    pos = {int(v): i for i, v in enumerate(hot_idx)}
    for i, a in enumerate(hot_idx):
        for b in hot_idx[i+1:]:
            if b - a > 3: break
            if comp[a] == -1: comp[a] = cid
            if comp[b] == -1: comp[b] = cid
            # union-find style merge
    # proper union-find
    parent = list(range(len(hot_idx)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry: parent[rx] = ry
    for i in range(len(hot_idx)):
        for j in range(i+1, len(hot_idx)):
            if hot_idx[j] - hot_idx[i] > 3: break
            union(i, j)
    comp = {}
    for i, v in enumerate(hot_idx):
        comp.setdefault(find(i), []).append(int(v))
    mask2 = np.zeros(nd, bool)
    for members in comp.values():
        # component is a chain of hot days with gaps<=2; it's an MHW iff it contains a run of >=5 consecutive hot days
        has5 = False
        for k in range(len(members) - 4):
            if all(members[k+r] == members[k] + r for r in range(5)):
                has5 = True; break
        if has5:
            for v in members:
                mask2[v] = True
    return mask2

rng = np.random.default_rng(42)
bad = 0
for trial in range(20000):
    nd = rng.integers(1, 100)
    p = rng.uniform(0.1, 0.8)
    h = rng.random(nd) < p
    r1 = mhw_runs(h)
    m1 = np.zeros(nd, bool)
    for s, e in r1:
        m1[s:e+1] = True
    m2 = brute_mask(h)
    if not np.array_equal(m1, m2):
        bad += 1
        if bad <= 3:
            print("MISMATCH", h.astype(int), r1, m1.astype(int), m2.astype(int))
print("mismatches:", bad, "of 20000")
