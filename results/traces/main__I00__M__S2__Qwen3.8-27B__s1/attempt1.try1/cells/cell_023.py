import numpy as np, datetime as dt
st = np.load("/tmp/st.npy")
sea = np.load("/tmp/sea.npy")
thr_s = np.load("/tmp/thr_s.npy")
doy = np.load("/tmp/doy.npy")
j0, j1 = 4540, 4631
doy_t = doy[j0:j1+1]
T = st[sea]
hot = T >= thr_s[doy_t-1].T
base = dt.date(2004,6,1)
idx = np.argwhere(hot)
print("hot cell-days:", len(idx))
cellmap = np.where(sea)[0]
for i, t in idx:
    ci = cellmap[i]
    print("cell %d, %s, SST %.3f thr %.3f diff %.4f" % (ci, str(base+dt.timedelta(days=t)), T[i,t], thr_s[doy_t[t]-1][i], T[i,t]-thr_s[doy_t[t]-1][i]))

# self-test of run detection + gap joining
def detect(h):
    x = np.concatenate([[0], h.astype(np.int8), [0]])
    d = np.diff(x)
    starts = np.where(d == 1)[0] + 1
    ends = np.where(d == -1)[0]
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    merged = []
    for s, e in zip(starts.tolist(), ends.tolist()):
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    m = np.zeros(len(h), dtype=bool)
    for s, e in merged:
        m[s:e+1] = True
    return m, merged

H = "11111"   # single run of 5
assert detect(np.array(list(H)== "1"))[1] == [(0,4)]
# 4 hot, gap 2, 4 hot -> no MHW (two-stage rule)
h = [1,1,1,1,0,0,1,1,1,1]
r, m = detect(np.array(h, bool))
print("case 4+gap2+4:", m, "expect []")
# 5 hot, gap 1, 3 hot -> one MHW 0..8
h = [1,1,1,1,1,0,1,1,1,0]
r, m = detect(np.array(h, bool))
print("case 5+gap1+3:", m, "expect [(0,8)]")
# 5 hot gap 3 5 hot -> two MHWs
h = [1,1,1,1,1,0,0,0,1,1,1,1,1,0]
r, m = detect(np.array(h, bool))
print("case 5+gap3+5:", m, "expect [(0,4),(8,12)]")
# 5 hot gap2 5 hot gap1 5 hot -> one MHW 0..14
h = [1]*5+[0,0]+[1]*5+[0]+[1]*5+[0,0,0]
r, m = detect(np.array(h, bool))
print("case chained:", m, "expect [(0,14)]")
# 4 hot gap 2 5 hot -> MHW only from index 7
h = [1,1,1,1,0,0,1,1,1,1,1,0,0,0]
r, m = detect(np.array(h, bool))
print("case 4+gap2+5:", m, "expect [(6,10)]")
print("self-tests done")
