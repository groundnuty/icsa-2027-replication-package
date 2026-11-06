import numpy as np
from datetime import date, timedelta

# --- synthetic test of MHW joining logic ---
def mhw_mask(h):
    n = len(h)
    out = np.zeros(n, dtype=bool)
    idx = np.where(h)[0]
    if idx.size == 0:
        return out
    brk = np.where(np.diff(idx) > 1)[0] + 1
    runs = list(np.split(idx, brk))
    evs = []
    last_i = -1
    for i, r in enumerate(runs):
        if len(r) >= 5:
            if evs and i == last_i + 1 and (r[0] - (runs[last_i][-1] + 1)) <= 2:
                evs[-1] = (evs[-1][0], r[-1])
            else:
                evs.append((r[0], r[-1]))
            last_i = i
    for s_, e_ in evs:
        out[s_:e_+1] = True
    return out

def H(s): return np.array([c=='1' for c in s])

# 5 hot, gap1, 5 hot -> one event covering 11
t1 = mhw_mask(H("0"*3 + "1"*5 + "0" + "1"*5 + "0"*3))
print("t1:", t1.astype(int).tolist(), "expect 1s at 3..12")
# gap2 join
t2 = mhw_mask(H("1"*5 + "00" + "1"*5))
print("t2:", t2.astype(int).tolist(), "expect 1s at 0..11")
# gap3 no join
t3 = mhw_mask(H("1"*5 + "000" + "1"*5))
print("t3:", t3.astype(int).tolist(), "expect two blocks")
# short run between two MHWs -> no join (separation contains hot days)
t4 = mhw_mask(H("1"*5 + "0" + "11" + "0" + "1"*5))
print("t4:", t4.astype(int).tolist(), "expect blocks 0-4 and 9-13 (no join)")
# short run + gap: 3-hot, gap1, 5-hot -> only the 5-hot is MHW
t5 = mhw_mask(H("1110" + "1"*5))
print("t5:", t5.astype(int).tolist(), "expect 1s at 4..8")
# chained joins: 5, gap1, 4(short), gap1, 5 -> 5 and 5 separated by hot short run -> no join
t6 = mhw_mask(H("1"*5 + "0" + "1"*4 + "0" + "1"*5))
print("t6:", t6.astype(int).tolist(), "expect 0-4 and 10-14")
# 5, gap1, 5, gap1, 5 all join
t7 = mhw_mask(H("1"*5 + "0" + "1"*5 + "0" + "1"*5))
print("t7:", t7.astype(int).tolist(), "expect 0..14")
