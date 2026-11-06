
import numpy as np, datetime as dt
hot = np.load('/tmp/hot.npy'); sea = np.load('/tmp/sea.npy'); mhwA = np.load('/tmp/mhwA.npy')
NC=3600

def cell_mhw_C(h):  # alternative 'closing' interpretation
    n=len(h); runs=[]; i=0
    while i < n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            runs.append((i,j-1)); i=j
        else: i+=1
    m=np.zeros(n,bool)
    if not runs: return m
    comps=[]; cs=0
    for k in range(1,len(runs)):
        if runs[k][0]-runs[k-1][1]-1>2: comps.append(runs[cs:k]); cs=k
    comps.append(runs[cs:])
    for comp in comps:
        if any(e-s+1>=5 for s,e in comp):
            m[comp[0][0]:comp[-1][1]+1]=True
    return m

diffC=0; totC=0
for c in range(NC):
    if not sea[c]: continue
    mC = cell_mhw_C(hot[:,c])
    totC += int((mC != mhwA[:,c]).sum())
    if (mC != mhwA[:,c]).any(): diffC+=1
print("cells where closing differs from literal:", diffC, "differing days:", totC)

# regional active days and events
tor = np.load('/tmp/tdates.npy')
active = mhwA.any(axis=1)
print("active days:", int(active.sum()), "of 92")
events=[]
i=0
while i < 92:
    if active[i]:
        j=i
        while j+1<92 and active[j+1]: j+=1
        events.append((dt.date.fromordinal(int(tor[i])), dt.date.fromordinal(int(tor[j]))))
        i=j+1
    else: i+=1
print("events:")
for s,e in events: print(" ", s, "->", e, "len", (e-s).days+1)

# invariant checks on mhwA
ok=True
for c in range(NC):
    if not sea[c]: continue
    h=hot[:,c]; m=mhwA[:,c]
    if m.sum()==0: continue
    # (1) every MHW day within 2 of a hot day
    dh = np.zeros(92)
    hd = h.astype(int)
    pad = np.r_[hd, [0,0]]
    for t in np.where(m)[0]:
        if not h[max(0,t-2):t+3].any(): ok=False; print("inv1 fail", c, t); break
    # (2) each MHW interval contains >=5 consecutive hot days
    runs=[]
    i=0
    while i<92:
        if m[i]:
            j=i
            while j+1<92 and m[j+1]: j+=1
            seg = h[i:j+1]
            # max run in seg
            best=0; cur=0
            for v in seg:
                cur = cur+1 if v else 0
                best=max(best,cur)
            if best<5: ok=False; print("inv2 fail", c, i, j)
            i=j+1
        else: i+=1
print("invariants:", "ok" if ok else "FAIL")
np.save('/tmp/active.npy', active)
