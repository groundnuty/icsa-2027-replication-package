
import numpy as np
hot = np.load('/tmp/hot.npy'); sea = np.load('/tmp/sea.npy')
mhwA = np.load('/tmp/mhwA.npy'); mhwB = np.zeros_like(mhwA)

def cell_mhw_A(h):
    n = len(h); runs=[]; i=0
    while i < n:
        if h[i]:
            j=i
            while j+1<n and h[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    qual=[(s,e) for s,e in runs if e-s+1>=5]
    merged=[]
    for s,e in qual:
        if merged and s-merged[-1][1]-1<=2: merged[-1][1]=e
        else: merged.append([s,e])
    m=np.zeros(n,bool)
    for s,e in merged: m[s:e+1]=True
    return m

def cell_mhw_B(h):
    n=len(h); runs=[]; i=0
    while i < n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            runs.append([i,j-1]); i=j
        else: i+=1
    m=np.zeros(n,bool)
    if not runs: return m
    comps=[]; cs=0
    for k in range(1,len(runs)):
        if runs[k][0]-runs[k-1][1]-1>2: comps.append(runs[cs:k]); cs=k
    comps.append(runs[cs:])
    for comp in comps:
        qual_pos=[k for k in range(len(comp)) if comp[k][1]-comp[k][0]+1>=5]
        groups=[]
        for k in qual_pos:
            if groups and k==groups[-1][-1]+1: groups[-1].append(k)
            else: groups.append([k])
        for g in groups:
            s=comp[g[0]][0]; e=comp[g[-1]][1]
            m[s:e+1]=True
    return m

diff_cells = [c for c in range(3600) if sea[c] and not (mhwA[:,c]==cell_mhw_B(hot[:,c])).all()]
print("diff cells:", len(diff_cells))
for c in diff_cells[:5]:
    print("cell", c)
    print("hot :", hot[:,c].astype(int).tolist())
    print("A   :", cell_mhw_A(hot[:,c]).astype(int).tolist())
    print("B   :", cell_mhw_B(hot[:,c]).astype(int).tolist())
