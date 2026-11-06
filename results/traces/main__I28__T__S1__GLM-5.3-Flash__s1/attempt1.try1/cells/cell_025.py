import numpy as np, time
st = np.load('/tmp/stage2.npz')
sea, TGT, tk = st['sea'], st['tgt'], st['tk']
thr_sm = st['thr_sm']
nt, nla, nlo = TGT.shape
NC = nla*nlo
T = TGT.reshape(nt, NC)
thr_d = thr_sm[tk-1]
hot = (T >= thr_d) & np.isfinite(T) & np.isfinite(thr_d)
print("hot cell-days:", int(hot.sum()))

idx = np.arange(nt)[:, None]           # (nt,1) broadcasts over (nt,NC)
def prev_true(mask):                    # most recent index <= t where mask, else -1
    p = np.where(mask, idx, -1)
    return np.maximum.accumulate(p, axis=0)
def next_true(mask):                    # first index >= t where mask, else nt
    nx = np.where(mask, idx, nt)
    return np.minimum.accumulate(nx[::-1], axis=0)[::-1]

def detect(hotb, mode):
    if mode == 'C':
        hb = hotb.copy()
        ph, nh_ = prev_true(hb), next_true(hb)
        hb = hb | ((~hb) & (ph >= 0) & (nh_ <= nt-1) & ((nh_ - ph - 1) <= 2))
        pn = prev_true(~hb)             # run start = pn+1
        nn = next_true(~hb)
        return hb & ((nn - pn - 1) >= 5)
    pn = prev_true(~hotb); nn = next_true(~hotb)
    cores = hotb & ((nn - pn - 1) >= 5)   # run length = nn - (pn+1)
    if mode == 'A':
        pc, nc = prev_true(cores), next_true(cores)
        return cores | ((~cores) & (pc >= 0) & (nc <= nt-1) & ((nc - pc - 1) <= 2))
    # mode B: join if gap between consecutive cores has <= 2 NON-HOT days
    nonhot = ~hotb
    c = np.concatenate([np.zeros((1, NC), dtype=np.int64), np.cumsum(nonhot, axis=0)], axis=0)
    pc, nc = prev_true(cores), next_true(cores)
    nonhot_gap = c[np.clip(nc, 0, nt), np.arange(NC)] - c[np.clip(pc+1, 0, nt), np.arange(NC)]
    return cores | ((~cores) & (pc >= 0) & (nc <= nt-1) & (nonhot_gap <= 2))

res = {}
for mode in 'ABC':
    m = detect(hot, mode)
    res[mode] = m
    actdays = m.sum(axis=1).astype(bool).sum()
    print(f"mode {mode}: MHW cell-days={int(m.sum())}, active days={int(actdays)}")

def brute(b, mode):
    n=len(b); mhw=[False]*n
    runs=[]; i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    cores=[(a,e) for a,e in runs if e-a+1>=5]
    if mode=='C':
        # fill first, then recompute runs
        bb=b.copy()
        changed=True
        while changed:
            changed=False
            i=0
            while i<n:
                if not bb[i]:
                    j=i
                    while j+1<n and not bb[j+1]: j+=1
                    if i>0 and j<n-1 and (j-i+1)<=2:
                        for t in range(i,j+1): bb[t]=True; changed=True
                    i=j+1
                else: i+=1
        b=bb
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
        ok = (gap<=2) if mode=='A' else (nh<=2)
        if ok:
            for t in range(e1+1,a2): mhw[t]=True
    return mhw

rng = np.random.default_rng(1)
cells = list(rng.choice(NC, 120, replace=False))
cells += list(np.argsort(hot.sum(0))[-15:])
allok = {m: True for m in 'ABC'}
for cc in cells:
    for mode in 'ABC':
        br = np.array(brute(hot[:,cc], mode), dtype=bool)
        if not np.array_equal(br, res[mode][:,cc]):
            allok[mode]=False
            print(f"mode {mode} mismatch cell {cc}: hot={''.join(map(str,hot[:,cc].astype(int)))}")
            print(f"  vec :{''.join(map(str,res[mode][:,cc].astype(int)))}")
            print(f"  brt :{''.join(map(str,br.astype(int)))}")
print("brute-check all ok:", allok)
np.savez('/tmp/stage3b.npz', hot=hot, A=res['A'], B=res['B'], C=res['C'], sea=sea)
