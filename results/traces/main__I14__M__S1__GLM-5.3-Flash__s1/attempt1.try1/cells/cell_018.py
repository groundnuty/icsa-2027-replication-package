import numpy as np, datetime as dt
from collections import Counter

z = np.load("/work/cache_sst.npz"); tgt32 = z["tgt"]; tgt_ord = z["tgt_ord"]
z2 = np.load("/work/cache_thr2.npz"); thr = z2["thr"]
zm = np.load("/work/cache_mhw.npz"); mhw = zm["mhw"]
tgt64 = tgt32.astype(np.float64)
tgt_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in tgt_ord], dtype=np.int32)
sea = np.all(np.isfinite(tgt64), axis=0)
hot = (tgt64 >= thr[tgt_doy-1]) & sea[None, :, :]

lens0, lens1, njoin, cells_with_runs = 0, [], 0, 0
total_joined_days = 0
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
        if not segs: continue
        cells_with_runs += 1
        lens0 += [e-s+1 for s,e in segs]
        joined = [list(segs[0])]
        for s,e in segs[1:]:
            if s-joined[-1][1]-1 <= 2: joined[-1][1]=e; njoin+=1
            else: joined.append([s,e])
        lens1 += [e-s+1 for s,e in joined]
        total_joined_days += sum(e-s+1 for s,e in joined)
print("cells with >=5d runs: %d | raw runs: %d (total %d d) | after join: %d segments (total %d d), joins: %d" %
      (cells_with_runs, len(lens0), sum(lens0), len(lens1), total_joined_days, njoin))
print("mhw mask cell-days:", int(mhw.sum()), "== sum joined lens:", total_joined_days)
print("joined segment length distribution:", dict(sorted(Counter(lens1).items())))
print("raw run length distribution:", dict(sorted(Counter(lens0).items())))

# edge cells: Jul 1 (2 cells) and Jul 8 (1 cell)
dates = [dt.date.fromordinal(int(o)) for o in tgt_ord]
for k, label in [(0, "Jul 1"), (7, "Jul 8")]:
    for i, j in np.argwhere(mhw[k]):
        print(f"{label} active cell ({i},{j}) hot Jun-Aug:", "".join(map(str, hot[:,i,j].astype(int))),
              "| mhw:", "".join(map(str, mhw[:,i,j].astype(int))))
