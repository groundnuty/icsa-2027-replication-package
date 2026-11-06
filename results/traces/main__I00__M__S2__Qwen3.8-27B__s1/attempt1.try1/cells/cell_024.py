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
lat = np.array([54.14, 55.32]); 
# reconstruct lat/lon of a cell: cell index = ilat*60 + ilon
import numpy as _np
for i, t in idx:
    ci = int(cellmap[i])
    ilat, ilon = divmod(ci, 60)
    print("cell %d (lat idx %d, lon idx %d), %s, SST %.3f thr %.3f diff %+.4f"
          % (ci, ilat, ilon, str(base+dt.timedelta(days=int(t))), float(T[i,t]), float(thr_s[doy_t[t]-1][i]), float(T[i,t]-thr_s[doy_t[t]-1][i])))

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

tests = [
 ("1"*5, [(0,4)]),
 ([1,1,1,1,0,0,1,1,1,1], []),
 ([1,1,1,1,1,0,1,1,1,0], [(0,8)]),
 ([1,1,1,1,1,0,0,0,1,1,1,1,1,0], [(0,4),(8,12)]),
 ([1]*5+[0,0]+[1]*5+[0]+[1]*5+[0,0,0], [(0,14)]),
 ([1,1,1,1,0,0,1,1,1,1,1,0,0,0], [(6,10)]),
 ([0]*92, []),
]
for h, expect in tests:
    if isinstance(h, str): h = [c=='1' for c in h]
    r, m = detect(np.array(h, dtype=bool))
    got = tuple(tuple(x) for x in m)
    print(("PASS" if got == tuple(map(tuple,expect)) else "FAIL"), h[:12], "got", got, "expect", expect)
    # mask check for one
    assert r.tolist() == [any(s<=k<=e for s,e in m) for k in range(len(h))]
print("self-tests done")
