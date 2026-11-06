import numpy as np, pandas as pd, pickle, json

with open('/tmp/stepA2.pkl','rb') as fh:
    D = pickle.load(fh)
thresh_s = D['thresh_s']
sst, sea = D['sst'], D['sea']
tdates, tdoy = D['tdates'], D['tdoy']
T = sst.shape[0]
sst_flat = sst.reshape(T, -1)

hot = np.zeros((T, 3600), dtype=bool)
hot[:, sea] = sst_flat[:, sea] >= thresh_s[tdoy - 1, :]
print("hot days total:", int(hot.sum()))

def per_cell_mhw(hot, min_run=5, max_gap=2):
    Tn, N = hot.shape
    padded = np.zeros((Tn + 2, N), dtype=np.int8)
    padded[1:-1] = hot
    dv = np.diff(padded, axis=0)
    sr, sc = np.where(dv == 1)
    er, ec = np.where(dv == -1)
    os_, oe = np.lexsort((sr, sc)), np.lexsort((er, ec))
    assert np.array_equal(sc[os_], ec[oe])
    sc, sr, ec, er = sc[os_], sr[os_], ec[oe], er[oe]
    L = er - sr
    keep = L >= min_run
    cc, cs, ce = sc[keep], sr[keep], er[keep]
    segs = []
    if len(cs):
        pc, ps, pe = int(cc[0]), int(cs[0]), int(ce[0])
        for c, s, e in zip(cc[1:], cs[1:], ce[1:]):
            c, s, e = int(c), int(s), int(e)
            if c == pc and s - pe <= max_gap:
                pe = e
            else:
                segs.append((pc, ps, pe)); pc, ps, pe = c, s, e
        segs.append((pc, ps, pe))
    mhw = np.zeros_like(hot)
    for c, s, e in segs:
        mhw[s:e, c] = True
    return mhw, segs, int(keep.sum()), len(cs)

mhw_flat, segs, n_runs5, n_runs_all = per_cell_mhw(hot)
print("runs total:", n_runs_all, "| runs >=5:", n_runs5, "| merged per-cell MHWs:", len(segs))
print("non-hot gap days inside MHWs:", int((mhw_flat & ~hot).sum()))

active = mhw_flat.any(axis=1)
events = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j + 1 < T and active[j + 1]: j += 1
        events.append((i, j)); i = j + 1
    else:
        i += 1
ev = [{"onset": str(tdates[a].date()), "end": str(tdates[b].date())} for a, b in events]
print("active days:", int(active.sum()), "/", T, "| events:", json.dumps(ev))
cnt = mhw_flat.sum(axis=1)
for t in range(T):
    if cnt[t] > 0:
        print(" ", tdates[t].date(), "cells in MHW:", int(cnt[t]))

def bf_runs(col):
    runs=[]; i=0; Tn=len(col)
    while i<Tn:
        if col[i]:
            j=i
            while j+1<Tn and col[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    return runs
mismatch=0
for c in range(3600):
    keep=[(s,e) for (s,e) in bf_runs(hot[:,c]) if e-s+1>=5]
    merged=[]
    if keep:
        cs,ce=keep[0]
        for s,e in keep[1:]:
            if s-ce<=2: ce=e
            else: merged.append((cs,ce)); cs,ce=s,e
        merged.append((cs,ce))
    exp=np.zeros(T,bool)
    for s,e in merged: exp[s:e+1]=True
    if not np.array_equal(exp, mhw_flat[:,c]): mismatch+=1
print("mask columns with mismatch vs brute force:", mismatch, "/ 3600")

mhw = mhw_flat.reshape(T, 60, 60).astype(np.uint8)
with open('/tmp/stepB2.pkl','wb') as fh:
    pickle.dump({'mhw': mhw, 'hot': hot.reshape(T,60,60), 'active': active, 'events': events, 'ev': ev,
                 'tdates': tdates, 'latvals': D['latvals'], 'lonvals': D['lonvals'], 'segs': segs}, fh)
print("saved stepB2")
