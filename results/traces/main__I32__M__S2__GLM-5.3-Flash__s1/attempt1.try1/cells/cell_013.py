import numpy as np, pickle
hot = np.load("/tmp/hot.npy"); mask = np.load("/tmp/mask_lit.npy"); fin = np.load("/tmp/fin_all.npy")
t0 = np.datetime64('2005-06-01')

# cell 1558 full hot series around event 1
print("cell 1558 hot, June 10-30:", hot[9:30, 1558].astype(int))
print("dates:", [(str(t0+np.timedelta64(i,'D'))[-5:]) for i in range(9,30)])

# random cells: print hot runs and joined events
rng = np.random.default_rng(7)
def runs(h):
    d = np.diff(np.concatenate([[0], h.view(np.int8), [0]]))
    st = np.where(d==1)[0]; en = np.where(d==-1)[0]-1
    return [(int(a),int(b)) for a,b in zip(st,en) if b-a+1>=5]
def join_lit(evs, h):
    out=[]
    for e in evs:
        if out:
            gs,ge = out[-1][1]+1, e[0]-1
            if 1<=e[0]-out[-1][1]-1<=2 and not h[gs:ge+1].any():
                out[-1]=(out[-1][0],e[1]); continue
        out.append(e)
    return out
sea_cols = np.where(fin)[0]
for c in rng.choice(sea_cols, 6, replace=False):
    ev = runs(hot[:,c]); jl = join_lit(ev, hot[:,c])
    print(f"cell {c}: runs>=5 {ev} -> joined {jl}")
    if jl != ev: 
        for s,e in jl: print("   joined event days:", [str(t0+np.timedelta64(i,'D'))[-5:] for i in range(s,e+1)], "hot:", hot[s:e+1,c].astype(int))

# final consistency: mask equals union of joined events per cell (already by construction); re-derive and compare
m2 = np.zeros_like(mask)
for c in range(3600):
    for s,e in join_lit(runs(hot[:,c]), hot[:,c]): m2[s:e+1, c] = 1
print("mask reconstruction identical:", np.array_equal(m2, mask))
# events list final
act = mask[:, fin].any(axis=1)
dd = np.diff(np.concatenate([[0], act.view(np.int8), [0]]))
evs = [(int(a),int(b)) for a,b in zip(np.where(dd==1)[0], np.where(dd==-1)[0]-1)]
print("FINAL regional events:", [(str(t0+np.timedelta64(s,'D')), str(t0+np.timedelta64(e,'D'))) for s,e in evs])
