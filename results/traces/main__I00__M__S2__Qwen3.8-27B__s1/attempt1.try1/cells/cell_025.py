import numpy as np, datetime as dt

st = np.load("/tmp/st.npy"); sea = np.load("/tmp/sea.npy")
thr_s = np.load("/tmp/thr_s.npy"); doy = np.load("/tmp/doy.npy")
j0, j1 = 4540, 4631
doy_t = doy[j0:j1+1]
T = st[sea]
hot = T >= thr_s[doy_t-1].T

def detect(h):
    x = np.concatenate([[0], h.astype(np.int8), [0]])
    d = np.diff(x)
    starts = np.where(d == 1)[0]        # original 0-based start
    ends   = np.where(d == -1)[0] - 1   # original 0-based end (inclusive)
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
 ([1,1,1,1,1,0,0,1,1,1,1,1,0], [(0,10)]),  # 5 + gap2 + 5
]
ok = True
for h, expect in tests:
    if isinstance(h, str): h = [c=='1' for c in h]
    r, m = detect(np.array(h, dtype=bool))
    got = tuple(tuple(x) for x in m)
    exp = tuple(map(tuple, expect))
    status = "PASS" if got == exp else "FAIL"
    ok &= (got == exp)
    print(status, got, "expect", exp)
    assert r.tolist() == [any(s<=k<=e for s,e in m) for k in range(len(h))]
print("ALL PASS" if ok else "SOME FAILED")

# final detection
in_mhw = np.zeros((T.shape[0], 92), dtype=bool)
for i in range(T.shape[0]):
    m, _ = detect(hot[i])
    in_mhw[i] = m
mask = np.zeros((3600, 92), dtype=np.uint8)
mask[sea] = in_mhw
active = in_mhw.any(axis=0)
print("any MHW:", bool(in_mhw.any()), "active days:", int(active.sum()))

events = []
s = None
for t in range(92):
    if active[t] and s is None: s = t
    if (not active[t]) and s is not None:
        events.append((s, t-1)); s = None
if s is not None: events.append((s, 91))
print("events:", events)
np.save("/tmp/in_mhw.npy", in_mhw); np.save("/tmp/mask.npy", mask)
np.save("/tmp/events.npy", np.array(events, dtype=int) if events else np.zeros((0,2), dtype=int))
print("saved")
