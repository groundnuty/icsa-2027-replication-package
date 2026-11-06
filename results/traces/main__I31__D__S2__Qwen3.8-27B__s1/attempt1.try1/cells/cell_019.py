import numpy as np

def mhw_mask_of(hot, minlen=5, gap=2):
    n = len(hot)
    p = np.concatenate([[0], hot.astype(np.int8), [0]])
    df = np.diff(p)
    s = np.where(df == 1)[0]; e = np.where(df == -1)[0]
    ev = [[a, b] for a, b in zip(s, e) if (b - a) >= minlen]
    if not ev:
        return np.zeros(n, bool)
    merged = [ev[0]]
    for a, b in ev[1:]:
        if a - merged[-1][1] <= gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = np.zeros(n, bool)
    for a, b in merged:
        out[a:b] = True
    return out

def runs(mask):
    p = np.concatenate([[0], mask.astype(np.int8), [0]]); df = np.diff(p)
    return list(zip(np.where(df==1)[0], np.where(df==-1)[0]))

h = np.zeros(92, bool); h[10:15] = True
assert runs(mhw_mask_of(h)) == [(10, 15)]
h = np.zeros(92, bool); h[10:14] = True
assert runs(mhw_mask_of(h)) == []
h = np.zeros(92, bool); h[5:10] = True; h[12:17] = True
assert runs(mhw_mask_of(h)) == [(5, 17)]          # gap 2 -> merged incl. gap days
h = np.zeros(92, bool); h[5:10] = True; h[13:18] = True
assert runs(mhw_mask_of(h)) == [(5, 10), (13, 18)]  # gap 3 -> separate
# transitive: A(5) gap1 B(5) gap1 C(5) -> single event (0,15)
h = np.zeros(92, bool); h[0:5] = True; h[6:11] = True; h[12:17] = True
assert runs(mhw_mask_of(h)) == [(0, 17)], runs(mhw_mask_of(h))
# non-MHW 3-day gap between two MHWs: no bridge (gap of 5 days)
h = np.zeros(92, bool); h[0:5] = True; h[6:9] = True; h[10:15] = True
assert runs(mhw_mask_of(h)) == [(0, 5), (10, 15)], runs(mhw_mask_of(h))
h = np.zeros(92, bool); h[0:5] = True; h[87:92] = True
assert runs(mhw_mask_of(h)) == [(0, 5), (87, 92)]
h = np.zeros(92, bool); h[40] = True
assert runs(mhw_mask_of(h)) == []
h = np.ones(92, bool)
assert runs(mhw_mask_of(h)) == [(0, 92)]
# A(3) gap1 B(3): no run >=5 anywhere -> none
h = np.zeros(92, bool); h[20:23] = True; h[24:27] = True
assert runs(mhw_mask_of(h)) == []
# A(3) gap1 B(2) -> none
h = np.zeros(92, bool); h[20:23] = True; h[24:26] = True
assert runs(mhw_mask_of(h)) == []
print("all MHW run/merge unit tests passed")
