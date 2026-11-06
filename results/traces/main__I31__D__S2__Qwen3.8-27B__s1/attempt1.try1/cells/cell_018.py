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

# case 1: exactly 5 hot days -> event
h = np.zeros(92, bool); h[10:15] = True
assert runs(mhw_mask_of(h)) == [(10, 15)], runs(mhw_mask_of(h))
# case 2: 4 hot days -> none
h = np.zeros(92, bool); h[10:14] = True
assert runs(mhw_mask_of(h)) == []
# case 3: two 5-runs, gap 2 -> merged incl. gap days
h = np.zeros(92, bool); h[5:10] = True; h[12:17] = True
assert runs(mhw_mask_of(h)) == [(5, 17)], runs(mhw_mask_of(h))
# case 4: two 5-runs, gap 3 -> two events
h = np.zeros(92, bool); h[5:10] = True; h[13:18] = True
assert runs(mhw_mask_of(h)) == [(5, 10), (13, 18)]
# case 5: transitive merge A(5) gap1 B(3) gap1 C(5) -> one event
h = np.zeros(92, bool); h[0:5] = True; h[6:9] = True; h[10:15] = True
assert runs(mhw_mask_of(h)) == [(0, 15)], runs(mhw_mask_of(h))
# case 6: runs at both boundaries
h = np.zeros(92, bool); h[0:5] = True; h[87:92] = True
assert runs(mhw_mask_of(h)) == [(0, 5), (87, 92)]
# case 7: single hot day -> none; all hot -> one
h = np.zeros(92, bool); h[40] = True
assert runs(mhw_mask_of(h)) == []
h = np.ones(92, bool)
assert runs(mhw_mask_of(h)) == [(0, 92)]
# case 8: 6-run with internal single cold day: A(3) gap1 B(3) -> merged 7
h = np.zeros(92, bool); h[20:23] = True; h[24:27] = True
assert runs(mhw_mask_of(h)) == [(20, 27)]
# case 9: A(3) gap1 B(2): neither >=5 alone; gap<=2 but neither qualifies -> none
h = np.zeros(92, bool); h[20:23] = True; h[24:26] = True
assert runs(mhw_mask_of(h)) == [], runs(mhw_mask_of(h))
print("all MHW run/merge unit tests passed")
