import numpy as np, pickle

with open('/tmp/stepB.pkl','rb') as fh:
    B = pickle.load(fh)
hot3 = B['hot']; mhw3 = B['mhw']; tdates = B['tdates']
hot = hot3.reshape(hot3.shape[0], -1)
mhw = mhw3.reshape(mhw3.shape[0], -1)

# brute-force per-cell run extraction on a subset of columns
def bf_runs(col):
    runs = []
    i = 0; Tn = len(col)
    while i < Tn:
        if col[i]:
            j = i
            while j+1 < Tn and col[j+1]: j += 1
            runs.append((i, j, j-i+1)); i = j+1
        else:
            i += 1
    return runs

all_bf = []
for c in range(hot.shape[1]):
    all_bf += [(c, s, e, L) for (s, e, L) in bf_runs(hot[:, c])]
Ls = np.array([r[3] for r in all_bf])
print("brute-force runs:", len(Ls), "total hot days:", int(hot.sum()))
import collections
cnt = collections.Counter(Ls.tolist())
print("run-length histogram (len:count), first 20:", sorted(cnt.items())[:20])
print("runs <5:", int((Ls < 5).sum()), "| runs >=5:", int((Ls >= 5).sum()))
print("mean run len:", Ls.mean(), "max:", Ls.max())

# verify mhw mask equals brute-force merged segments (min_run 5, gap<=2)
mismatch = 0
for c in range(hot.shape[1]):
    runs = bf_runs(hot[:, c])
    keep = [(s, e) for (s, e, L) in runs if L >= 5]
    merged = []
    if keep:
        cs, ce = keep[0]
        for s, e in keep[1:]:
            if s - ce <= 2: ce = e
            else: merged.append((cs, ce)); cs, ce = s, e
        merged.append((cs, ce))
    exp = np.zeros(92, bool)
    for s, e in merged: exp[s:e+1] = True
    if not np.array_equal(exp, mhw[:, c]):
        mismatch += 1
        if mismatch <= 3:
            print("MISMATCH col", c, "expected", np.where(exp)[0][:50], "got", np.where(mhw[:,c])[0][:50])
print("columns with mismatch:", mismatch, "/", hot.shape[1])
