import numpy as np
st = np.load("cache/stage1.npz")
d = np.load("cache/region.npz")
hot = st['hot']; tt = d['time_tgt']
NT = 92

def runs_of(x):
    x = np.asarray(x, dtype=bool)
    dd = np.diff(x.view(np.int8))
    starts = [int(i)+1 for i in np.flatnonzero(dd == 1)] + ([0] if x[0] else [])
    ends   = [int(i)     for i in np.flatnonzero(dd == -1)] + ([len(x)-1] if x[-1] else [])
    return list(zip(starts, ends))

# unit test
x = np.array([0,1,1,1,1,1,0,1,1,1,1,1,1,0])
assert runs_of(x) == [(1,5),(7,12)], runs_of(x)
x = np.array([1,1,0,0])
assert runs_of(x) == [(0,1)]
x = np.array([0,0,1,1])
assert runs_of(x) == [(2,3)]
print("runs_of unit tests PASS")

nsea = mhw_shape = hot.shape[1]
mhw = np.zeros((NT, nsea), dtype=np.uint8)
for ci in range(nsea):
    cand = [r for r in runs_of(hot[:, ci]) if r[1] - r[0] + 1 >= 5]
    merged = []
    for s, e in cand:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for s, e in merged:
        mhw[s:e+1, ci] = 1

active = mhw.any(axis=1)
events = runs_of(active)
print("events:", [(str(tt[s])[:10], str(tt[e])[:10], e-s+1) for s, e in events])
for s, e in events:
    before = active[s-1] if s > 0 else None
    after  = active[e+1] if e < 91 else None
    print(f"  {tt[s][:10]} .. {tt[e][:10]}  len={e-s+1}  active_before={before} active_after={after}")
print("active days:", int(active.sum()), " cells with MHW:", int((mhw.sum(0)>0).sum()))

np.savez_compressed("cache/stage2.npz", mhw=mhw, events=np.array(events, dtype=int).reshape(-1,2) if events else np.zeros((0,2), int))
print("stage2 saved")