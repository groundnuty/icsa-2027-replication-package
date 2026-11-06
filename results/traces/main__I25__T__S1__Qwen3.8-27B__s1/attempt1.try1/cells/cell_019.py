
import numpy as np, time
sst_tgt = np.load('/tmp/sst_tgt.npy')      # (92, 3600)
thr_s   = np.load('/tmp/thr_s.npy')        # (366, 3600)
t_doy   = np.load('/tmp/t_doy.npy')        # (92,)
NC = 3600
t0=time.time()

sea = np.isfinite(sst_tgt).all(axis=0)
print("sea cells:", int(sea.sum()), "land:", int((~sea).sum()))

thr_t = thr_s[t_doy-1]          # (92, 3600)
hot = sst_tgt >= thr_t          # NaN comparisons -> False
print("hot days total:", int(hot.sum()), "min/max hot per day:", hot.sum(axis=1).min(), hot.sum(axis=1).max())

def cell_mhw_A(h):
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]: j += 1
            runs.append((i, j)); i = j+1
        else: i += 1
    qual = [(s,e) for s,e in runs if e-s+1 >= 5]
    merged = []
    for s,e in qual:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    m = np.zeros(n, bool)
    for s,e in merged: m[s:e+1] = True
    return m

def cell_mhw_B(h):  # independent: build components of runs connected by gap<=2,
    # literal merge: within component, consecutive qual runs merge only if adjacent runs
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]: j += 1
            runs.append([i, j-1]); i = j
        else: i += 1
    m = np.zeros(n, bool)
    comp_start = 0
    comps = []
    for k in range(1, len(runs)):
        s_prev, e_prev = runs[k-1]; s, e = runs[k]
        if s - e_prev - 1 > 2: comps.append(runs[comp_start:k]); comp_start = k
    if runs: comps.append(runs[comp_start:])
    for comp in comps:
        qual_pos = [k for k in range(len(comp)) if comp[k][1]-comp[k][0]+1 >= 5]
        merged_idx = []
        for k in qual_pos:
            if merged_idx and k == merged_idx[-1]+1:
                merged_idx[-1] = k
            else:
                merged_idx.append(k)
        for g in merged_idx:
            s, e = comp[g]
            while g+1 in merged_idx:
                g += 1; e = comp[g][1]
            m[s:e+1] = True
    return m

# quick sanity on examples
ex = [0,0,1,1,1,1,1,0,1,1,1,1,1,0,0,1,1,1,1,1,1,1,1]  # 5 + gap1 + 7 -> merge
print("A:", cell_mhw_A(np.array(ex,dtype=bool)).astype(int).tolist())
ex2 = [0,1,1,1,0,0,1,1,1,1,1]  # 3 + gap2 + 5 -> A and B? B alone
print("A2:", cell_mhw_A(np.array(ex2,dtype=bool)).astype(int).tolist())
ex3 = [1,1,1,1,1,0,1,0,0,1,1,1,1,1]  # 5 + gap1(short1) + gap2 + 5 -> literal: no merge
print("A3:", cell_mhw_A(np.array(ex3,dtype=bool)).astype(int).tolist())

mhwA = np.zeros((92, NC), bool)
for c in range(NC):
    if not sea[c]: continue
    mhwA[:, c] = cell_mhw_A(hot[:, c])
mhwB = np.zeros((92, NC), bool)
for c in range(NC):
    if not sea[c]: continue
    mhwB[:, c] = cell_mhw_B(hot[:, c])
print("A vs B identical:", bool((mhwA == mhwB).all()))
print("MHW cell-days:", int(mhwA.sum()), "cells with MHW:", int(mhwA.any(axis=0).sum()))
np.save('/tmp/mhwA.npy', mhwA)
np.save('/tmp/sea.npy', sea)
np.save('/tmp/hot.npy', hot)
print("done %.1f s" % (time.time()-t0))
