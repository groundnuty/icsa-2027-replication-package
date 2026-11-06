
import numpy as np, pickle
M_a = np.load('/work/work/M_a.npy')
M_old = np.load('/work/work/M.npy')
hot = np.load('/work/work/hot.npy')
n = hot.shape[1]

def runs_of(b):
    out = []; i = 0
    while i < len(b):
        if b[i]:
            j = i
            while j+1 < len(b) and b[j+1]: j += 1
            out.append((i,j)); i = j+1
        else: i += 1
    return out

changed = [j for j in range(n) if not np.array_equal(M_a[:,j], M_old[:,j])]
print("changed cells:", len(changed))
kinds = {}
for j in changed:
    # find where they differ
    d = np.where(M_a[:,j] != M_old[:,j])[0]
    # the removed days (in old not in new) must form the nh-h-nh gap: 3 days, middle hot, between two runs>=5
    rem = M_old[:,j] & ~M_a[:,j]
    rd = np.where(rem)[0]
    ok = (len(rd)==3 and hot[rd[1],j] and not hot[rd[0],j] and not hot[rd[2],j]
          and np.all(M_old[rd[0]-1:rd[0],j]) and np.all(M_old[rd[2]+1:rd[2]+2,j]))
    # also ensure the surrounding MHW runs are >=5 in hot
    a = rd[0]-1
    while a>=0 and hot[a,j]: a-=1
    b = rd[2]+1
    while b<92 and hot[b,j]: b+=1
    left_run = a+1 if a>=0 else 0
    kinds[j] = (bool(ok), (a+1, rd[0]-1), (rd[2]+1, b-1))
bad = [j for j,v in kinds.items() if not v[0]]
print("changed cells not matching nh-h-nh removal pattern:", bad)
print("example:", changed[0], kinds[changed[0]])
# verify final M_a: every M run is union of runs>=5 joined by <=2 all-nonhot gaps (equivalently gap<=2)
viol = 0
for j in range(n):
    for (a,b) in runs_of(M_a[:,j]):
        # cover [a,b] by hot runs of >=5 with gaps <=2
        hs = [(x,y) for (x,y) in runs_of(hot[a:b+1,j]) if y-x+1>=5]
        if not hs: viol+=1; continue
        if hs[0][0]!=0 or hs[-1][1]!=b-a: viol+=1; continue
        for k2 in range(len(hs)-1):
            if hs[k2+1][0]-hs[k2][1]-1 > 2: viol+=1
        # ensure no extra hot runs >? (short runs may be inside, fine)
print("M_a structural violations:", viol)
# active/event recheck with M_a
active = M_a.any(axis=1)
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
td = D['target']
ev = []
i=0
while i<92:
    if active[i]:
        j2=i
        while j2+1<92 and active[j2+1]: j2+=1
        ev.append((td[i].isoformat(), td[j2].isoformat(), j2-i+1)); i=j2+1
    else: i+=1
print("final events:", ev, " active days:", int(active.sum()))
