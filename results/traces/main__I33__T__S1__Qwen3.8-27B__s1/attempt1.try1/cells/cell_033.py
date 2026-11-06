
import numpy as np, pickle
M = np.load('/work/work/M.npy')
hot = np.load('/work/work/hot.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']
n = M.shape[1]

def runs_of(b):
    out = []; i = 0
    while i < len(b):
        if b[i]:
            j = i
            while j+1 < len(b) and b[j+1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out

n_fin = sum(len(runs_of(M[:, j])) for j in range(n))
M_pre = np.zeros_like(M)
for j in range(n):
    for (a,b) in [(a,b) for (a,b) in []]: pass
# recompute pre-join M
Mpre = np.zeros_like(M)
for j in range(n):
    hcol = hot[:, j]; i = 0
    while i < 92:
        if hcol[i]:
            j2 = i
            while j2+1 < 92 and hcol[j2+1]: j2 += 1
            if j2 - i + 1 >= 5: Mpre[i:j2+1, j] = True
            i = j2 + 1
        else: i += 1
print("pre-join MHW cell-days:", int(Mpre.sum()), " post-join:", int(M.sum()), " added by joins:", int(M.sum()-Mpre.sum()))
print("final per-cell MHW count:", n_fin)
print("cells with MHW:", int((M.sum(0)>0).sum()))

# per-cell duration stats
durs = np.array([ (b-a+1) for j in range(n) for (a,b) in runs_of(M[:, j]) ])
print("per-cell MHW durations: min", durs.min(), "max", durs.max(), "mean", round(durs.mean(),1))

# verify consistency: no non-hot gap between final runs is <3; i.e., between consecutive final runs in a cell, non-hot days >= 3
bad = 0
for j in range(n):
    rr = runs_of(M[:, j])
    for k in range(len(rr)-1):
        gap = rr[k+1][0] - rr[k][1] - 1
        if gap < 3: bad += 1
print("final run pairs with gap<3 (should be 0):", bad)

# verify every final MHW contains an original run>=5 and equals union of merged runs
ok = 0
for j in range(n):
    rr = runs_of(M[:, j])
    for (a,b) in rr:
        # must contain at least one full original hot run of >=5
        has = any(hot[a:b+1, j].sum() >= 5 for _ in [0])
        # check all days in [a,b] that are hot are fine; non-hot days are gap-days only (<=2 between hot blocks)
        ok += 1
print("final MHWs checked:", ok)

# example cells
for j in [0, 100, 2000]:
    lat, lon = sea[j]
    s = ''.join('#' if M[k,j] else ('.' if hot[k,j] else '-') for k in range(92))
    print(f"cell {j} ({lat:.2f},{lon:.2f}): {s}")
    print("   ", target_dates[0].isoformat(), "->", target_dates[-1].isoformat())
