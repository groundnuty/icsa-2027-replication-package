import numpy as np, pickle

with open("/tmp/mhw_state.pkl","rb") as f: S = pickle.load(f)
with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/thr.pkl","rb") as f: T = pickle.load(f)

hot = S["hot"]; mhw_mask = S["mhw_mask"]; active = S["active"]
time_target = D["time_target"]

print("daily hot-cell counts:")
for i in range(92):
    print(i+1, time_target[i].strftime("%m-%d"), int(hot.sum(axis=1)[i]), end="   ")
    if (i+1) % 10 == 0: print()
print()
print("active days (1-based):", [i+1 for i in range(92) if active[i]])

# show one cell with an MHW: its hot pattern and MHW span
c = int(np.where(mhw_mask.any(axis=0))[0][0])
print("\ncell", c, "hot:", hot[:, c].astype(int).tolist())
print("cell", c, "mhw:", mhw_mask[:, c].astype(int).tolist())
spans = []
i = 0
while i < 92:
    if mhw_mask[i, c]:
        j = i
        while j+1 < 92 and mhw_mask[j+1, c]: j += 1
        spans.append((i+1, j+1)); i = j+1
    else: i += 1
print("mhw spans (1-based days):", spans)

# verify merge behaviour exists somewhere: count cells where merged span > last hot run end
cnt_merge = 0
def runs_of(mask):
    out, n, i = [], len(mask), 0
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j+1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out
for c in range(mhw_mask.shape[1]):
    if mhw_mask.any(0) and False: pass
for c in range(mhw_mask.shape[1]):
    ms = mhw_mask[:, c]
    if not ms.any(): continue
    hs = hot[:, c]
    runs5 = [r for r in runs_of(hs) if r[1]-r[0]+1 >= 5]
    merged = []
    for s, e in runs5:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    if len(merged) < len(runs5):
        cnt_merge += 1
print("cells where a merge reduced #runs:", cnt_merge)
