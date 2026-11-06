import numpy as np, datetime as dt

def cell_segments(hot):
    n = len(hot); segs = []; i = 0
    while i < n:
        if hot[i]:
            j = i
            while j < n and hot[j]: j += 1
            if j - i >= 5: segs.append((i, j-1))
            i = j
        else: i += 1
    if not segs: return []
    joined = [list(segs[0])]
    for s, e in segs[1:]:
        if s - joined[-1][1] - 1 <= 2: joined[-1][1] = e
        else: joined.append([s, e])
    return [tuple(x) for x in joined]

# corrected expectations
cases = [
    ([1]*5+[0]+[1]*5, [(0,10)]),               # 5+1gap+5 = 11 days, join
    ([1]*5+[0,0]+[1]*5, [(0,11)]),             # 5+2gap+5 = 12 days, join
    ([1]*5+[0,0,0]+[1]*5, [(0,4),(8,12)]),     # 3-day gap: no join
    ([1]*4+[0]+[1]*5, [(5,9)]),                # 4-day run dropped
    ([0]*3+[1]*7+[0]*2+[1]*5+[0], [(3,16)]),   # 7+2gap+5 = 14 days: indices 3..16, join
    ([1]*10, [(0,9)]),
    ([1]*4, []),
    ([0,1,1,1,1,1,1,1,1,1,1,1,1,0], [(1,12)]),
]
ok = all(cell_segments(np.array(h,dtype=bool)) == e for h, e in cases)
for h, e in cases:
    g = cell_segments(np.array(h,dtype=bool))
    print(" ", h, "->", g, "OK" if g==e else "FAIL")
print("synthetic tests (corrected expectations):", ok)

# real data: confirm no joins occurred, lengths consistent
z = np.load("/work/cache_sst.npz"); tgt32 = z["tgt"]; tgt_ord = z["tgt_ord"]
z2 = np.load("/work/cache_thr2.npz"); thr = z2["thr"]
zm = np.load("/work/cache_mhw.npz"); mhw = zm["mhw"]
tgt64 = tgt32.astype(np.float64)
tgt_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in tgt_ord], dtype=np.int32)
sea = np.all(np.isfinite(tgt64), axis=0)
hot = (tgt64 >= thr[tgt_doy-1]) & sea[None, :, :]

lens0, lens1, njoin = [], [], 0
for i in range(60):
    for j in range(60):
        if not sea[i,j] or not hot[:,i,j].any(): continue
        h = hot[:,i,j]; n=92; k=0; segs=[]
        while k < n:
            if h[k]:
                m = k
                while m < n and h[m]: m += 1
                if m-k >= 5: segs.append((k,m-1))
                k = m
            else: k += 1
        lens0 += [e-s+1 for s,e in segs]
        joined = [list(segs[0])]
        for s,e in segs[1:]:
            if s-joined[-1][1]-1 <= 2: joined[-1][1]=e; njoin+=1
            else: joined.append([s,e])
        lens1 += [e-s+1 for s,e in joined]
print("raw runs: %d, total days %d | after join: %d segments, total days %d, joins performed: %d" %
      (len(lens0), sum(lens0), len(lens1), sum(lens1), njoin))
print("mhw mask cell-days:", int(mhw.sum()), "== sum of joined lens:", sum(lens1))
from collections import Counter
print("run length distribution:", dict(sorted(Counter(lens1).items())))

# edge cells: the 2 cells active on Jul 1, the 1 cell active on Jul 8
dates = [dt.date.fromordinal(int(o)) for o in tgt_ord]
for k, label in [(0, "Jul 1 active cells"), (7, "Jul 8 active cells")]:
    for i, j in np.argwhere(mhw[k]):
        h = hot[:, i, j].astype(int)
        print(f"{label}: cell ({i},{j}) hot pattern Jun-Aug:",
              "".join(str(x) for x in h),
              "| mhw:", "".join(str(x) for x in mhw[:,i,j]))
