import numpy as np

# --- debug the single failing case in extreme detail ---
hotr = [True]*5 + [False]*2 + [True]*5 + [False]*82
hot = np.array(hotr, bool)
hpad = np.array([False] + list(hot) + [False])
print("hpad first 15:", hpad[:15].astype(int).tolist())
d = np.diff(hpad.astype(np.int8))
print("d first 15:", d[:15].tolist())
starts = np.where(d == 1)[0]
ends = np.where(d == -1)[0] - 1
print("starts:", starts.tolist(), "ends:", ends.tolist())
runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
print("runs:", runs)
merged = []
for s, e in runs:
    if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
    else: merged.append([s, e])
print("merged:", merged)
out = np.zeros(92, bool)
for s, e in merged: out[s:e+1] = True
print("out nonzero idx:", np.where(out)[0].tolist())
exp = np.zeros(92, bool); exp[0:12] = True
print("match:", np.array_equal(out, exp))
