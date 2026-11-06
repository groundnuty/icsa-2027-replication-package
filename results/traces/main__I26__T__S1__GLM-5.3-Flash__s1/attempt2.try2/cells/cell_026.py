import numpy as np
def detect(h):
    T=len(h); m=np.zeros(T,np.uint8)
    idx=np.where(h)[0]
    if idx.size==0: return m
    br=np.where(np.diff(idx)>1)[0]
    st=np.r_[idx[0],idx[br+1]]; en=np.r_[idx[br],idx[-1]]
    keep=(en-st+1)>=5
    if not keep.any(): return m
    st,en=st[keep],en[keep]
    cs,ce=st[0],en[0]; segs=[]
    for k in range(1,len(st)):
        if st[k]-ce-1<=2: ce=en[k]
        else: segs.append((cs,ce)); cs,ce=st[k],en[k]
    segs.append((cs,ce))
    for a,b in segs: m[a:b+1]=1
    return m
def nev(m):
    n=0; prev=0
    for v in m:
        if v and not prev: n+=1
        prev=v
    return n
# corrected tests
tests = [
    ([1,1,1,1,0,0,1,1,1,1,0,0,0,1,1,1,1,1], 1),            # runs 4,4,5 -> only last kept
    ([1,1,1,1,1,0,0,1,1,1,1,1,0,0,0,1,1,1,1,1], 2),        # 5,5,5; gap2 join, gap3 split -> 2 events
    ([1,1,1,1,1,0,0,1,1,1,1,1,0,0,1,1,1,1,1], 1),          # 5,5,5; gaps 2,2 -> all joined -> 1 event
    ([1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1], 1),              # gaps 1,1 -> 1 event
    ([1,1,1,1,1,0,0,0,1,1,1,1,1,0,1,1,1,1,1], 2),          # gap3 split, gap1 join -> 2 events
    ([0,0,1,1,1,1,1,0,0,0,0,1,1,1,1,1,0,0,1,1,1,1,1], 2),  # gap4 split, gap2 join -> 2 events
]
for k,(h,nexp) in enumerate(tests):
    m=detect(np.array(h,bool)); n=nev(m)
    print(f'test{k}: events={n} expected={nexp}', 'OK' if n==nexp else 'FAIL')
