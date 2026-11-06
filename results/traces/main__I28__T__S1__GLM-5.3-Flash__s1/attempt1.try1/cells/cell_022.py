import numpy as np, json, time
from datetime import date, timedelta

st = np.load('/tmp/stage2.npz')
thr_sm, clim_sm, sea, TGT, tk = st['thr_sm'], st['clim_sm'], st['sea'], st['tgt'], st['tk']
nt, nla, nlo = TGT.shape          # 92, 60, 60
NC = nla*nlo
T = TGT.reshape(nt, NC)

# hot: SST >= threshold for that cell/day-of-year (NaN -> False)
thr_d = thr_sm[tk-1]              # (92, 3600)
hot = np.greater_equal(T, thr_d, where=np.isfinite(T) & np.isfinite(thr_d), out=np.zeros((nt,NC), dtype=bool))
# note: where= mask ensures NaN comparisons don't produce True; but np.greater_equal with where leaves out untouched (False init)
# recompute safely:
hot = (T >= thr_d)
hot &= np.isfinite(T) & np.isfinite(thr_d)
print("hot days total:", int(hot.sum()), " hot per day min/max:", int(hot.sum(1).min()), int(hot.sum(1).max()))

idx = np.arange(nt)[:, None]

def runs_and_fill(hotb, mode):
    """mode 'A': cores=hot runs>=5, fill gaps (consecutive non-core days between cores) of len<=2.
       mode 'B': cores=hot runs>=5, join cores whose gap contains <=2 NON-HOT days, filling all gap days.
       mode 'C': fill non-hot gaps of len<=2 in hot series first, then runs>=5."""
    if mode == 'C':
        hb = hotb.copy()
        # fill runs of <=2 consecutive False between True runs
        p = np.where(hb, idx, -1); p = np.maximum.accumulate(p, axis=0)
        nx = np.where(hb, idx, nt); nx = np.minimum.accumulate(nx[::-1], axis=0)[::-1]
        gaplen = nx - p - 1
        hb = hb | ((~hb) & (p >= 0) & (nx <= nt-1) & (gaplen <= 2))
        # then runs >= 5
        d = np.where(hb, idx, 0); d = np.maximum.accumulate(d, axis=0)
        e = np.where(~hb, idx, nt); e = np.minimum.accumulate(e[::-1], axis=0)[::-1]
        return hb & ((e - d) >= 5)
    hb = hotb & True
    d = np.where(hb, idx, 0); d = np.maximum.accumulate(d, axis=0)
    e = np.where(~hb, idx, nt); e = np.minimum.accumulate(e[::-1], axis=0)[::-1]
    runlen = e - d
    cores = hb & (runlen >= 5)
    if mode == 'A':
        p = np.where(cores, idx, -1); p = np.maximum.accumulate(p, axis=0)
        nx = np.where(cores, idx, nt); nx = np.minimum.accumulate(nx[::-1], axis=0)[::-1]
        gaplen = nx - p - 1
        return cores | ((~cores) & (p >= 0) & (nx <= nt-1) & (gaplen <= 2))
    else:  # B: count non-hot days in each gap between consecutive cores
        # For non-core day t between prev core (p) and next core (nx): number of non-hot days in (p, nx) exclusive.
        # non-hot cumulative count: c[t] = number of non-hot days in [0, t)
        nonhot = ~hotb
        c = np.concatenate([np.zeros((1, NC), dtype=np.int64), np.cumsum(nonhot, axis=0)], axis=0)
        p = np.where(cores, idx, -1); p = np.maximum.accumulate(p, axis=0)
        nx = np.where(cores, idx, nt); nx = np.minimum.accumulate(nx[::-1], axis=0)[::-1]
        nonhot_in_gap = c[np.clip(nx,0,nt), np.arange(NC)] - c[np.clip(p+1,0,nt), np.arange(NC)]
        # careful: c[nx] - c[p+1] counts non-hot days in indices [p+1, nx-1] -> the gap days
        joinable = (p >= 0) & (nx <= nt-1) & (nonhot_in_gap <= 2)
        # fill only days within (p, nx)
        return cores | ((~cores) & joinable)

res = {}
for mode in 'ABC':
    m = runs_and_fill(hot, mode)
    res[mode] = m
    print(f"mode {mode}: MHW cell-days = {int(m.sum())}, days with any MHW = {int(m.any(0).sum() and m.sum(1).astype(bool).sum())}")

for a,b in [('A','B'),('A','C'),('B','C')]:
    diff = int((res[a] != res[b]).sum())
    print(f"A vs {b}: differing cell-days = {diff}")

def brute(b):
    n=len(b); mhw=[False]*n
    runs=[]; i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    cores=[(a,e) for a,e in runs if e-a+1>=5]
    for a,e in cores:
        for t in range(a,e+1): mhw[t]=True
    for (a1,e1),(a2,e2) in zip(cores,cores[1:]):
        gap = a2-e1-1
        nh = sum(1 for t in range(e1+1,a2) if not b[t])
        # A: gap<=2 ; B: non-hot<=2
        if gap<=2:
            for t in range(e1+1,a2): mhw[t]=True
    return mhw

rng = np.random.default_rng(0)
cells = list(rng.choice(NC, 80, replace=False))
cells += list(np.argsort(hot.sum(0))[-10:])   # most-hot cells
okA=okB=True
for cc in cells:
    br = np.array(brute(hot[:,cc]))
    if not np.array_equal(br, res['A'][:,cc]): okA=False; print("A mismatch cell", cc)
    # brute B
    n=nt; mhw=[False]*n
    runs=[]; i=0
    b=hot[:,cc]
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    cores=[(a,e) for a,e in runs if e-a+1>=5]
    for a,e in cores:
        for t in range(a,e+1): mhw[t]=True
    for (a1,e1),(a2,e2) in zip(cores,cores[1:]):
        nh = sum(1 for t in range(e1+1,a2) if not b[t])
        if nh<=2:
            for t in range(e1+1,a2): mhw[t]=True
    if not np.array_equal(np.array(mhw), res['B'][:,cc]): okB=False; print("B mismatch cell", cc)
print("brute A ok:", okA, " brute B ok:", okB)
np.savez('/tmp/stage3.npz', hot=hot, A=res['A'], B=res['B'], C=res['C'], sea=sea)
