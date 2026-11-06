import numpy as np
# unit tests of run-find + join logic (as implemented)
def detect(h, minlen=5, gap=2):
    idx=np.flatnonzero(h)
    mhw=np.zeros(len(h), bool)
    if idx.size==0: return mhw, []
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.concatenate(([idx[0]], idx[br+1])); ends=np.concatenate((idx[br],[idx[-1]]))
    seeds=[(int(s),int(e)) for s,e in zip(starts,ends) if e-s+1>=minlen]
    if not seeds: return mhw, []
    merged=[list(seeds[0])]
    for s,e in seeds[1:]:
        if s-merged[-1][1]-1<=gap: merged[-1][1]=e
        else: merged.append([s,e])
    for s,e in merged: mhw[s:e+1]=True
    return mhw, merged

tests = {
 "[5-run]": [1,1,1,1,1],
 "[4-run]": [1,1,1,1],
 "[4-run then 5-run]": [1,1,1,1,0,1,1,1,1,1],
 "[5+gap1+5]": [1,1,1,1,1,0,1,1,1,1,1],
 "[5+gap2+5]": [1,1,1,1,1,0,0,1,1,1,1,1],
 "[5+gap3+5]": [1,1,1,1,1,0,0,0,1,1,1,1,1],
 "[3+gap2+2]": [1,1,1,0,0,1,1],
 "[6-run]": [1]*6,
 "[4+gap1+4+gap1+4]": [1,1,1,1,0,1,1,1,1,0,1,1,1,1],
}
for name,h in tests.items():
    m,mrg=detect(np.array(h,bool))
    print(f"{name}: merged={mrg} mask={m.astype(int).tolist()}")
